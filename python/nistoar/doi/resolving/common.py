"""
Common functions and entry points for resolving a DOI to metadata
"""
import re, logging
import requests

default_doi_resolver = "https://doi.org/"

_url_server_re = re.compile(r'^https?://[^/]+/')

_client_info = None
def set_client_info(project, version, projecturl, email):
    """
    set the runtime-wide DOI client information.  This can be sent with
    queries to DOI information services to, as a courtesy, identify us as a
    user of the services.

    At the moment, this is supported by the Crossref services only.  (See
    the crossrefapi python package).  

    :param str project:     the name of the application accessing DOIs
    :param str version:     the version of the application
    :param str projecturl:  the URL for the home page for application/project
    :param str email:       a contact email address for the app/project
    """
    global _client_info
    if not project:
        _client_info = None
    else:
        _client_info = (project, version, projecturl, email)

def strip_DOI(doi, resolver=None):
    """
    strip off a legal prefixes from a given DOI so that it starts with the 
    authority string (i.e. "10...")

    :param str doi:       the DOI string to strip
    :param str resolver:  a non-standard DOI resolver base URL to allow for.  It
                          should include a trailing / or ? if these are relevent.
    """
    doi = doi.strip()
    if doi.startswith("doi:"):
        doi = doi[4:]
    elif resolver and doi.startswith(resolver):
        doi = doi[len(resolver):]
    elif doi.startswith(default_doi_resolver):
        doi = doi[len(default_doi_resolver):]
    elif _url_server_re.match(doi):
        doi = _url_server_re.sub('', doi)

    return doi

class CT(object):
    """
    an enumeration class for holding standard content type (MIME type) values
    as static attributes.  Note that not all resolvers support all these 
    defined types.

    See https://citation.crosscite.org/docs.html#sec-4.
    """
    Citeproc_JSON     = "application/vnd.citationstyles.csl+json"
    RDF_XML           = "application/rdf+xml"
    RDF_Turtle        = "text/turtle"
    citation_text     = "text/x-bibliography"
    Crossref_XML      = "application/vnd.crossref.unixref+xml"
    Datacite_XML      = "application/vnd.datacite.datacite+xml"
    Datacite_JSON     = "application/vnd.datacite.datacite+json"
    Schema_org_JSONLD = "application/vnd.schemaorg.ld+json"

class DOIInfo(object):
    """
    a class that gives access to metadata and views associated with a DOI.
    Some information will be cached internally when the object is created;
    other information may only be loaded when accessed.  Typically the 
    information is loaded from a REST call to a DOI resolver.  
    """

    def __init__(self, doi, source="unknown", resolver=None, logger=None):
        if not resolver:
            resolver = default_doi_resolver
        self.resolver = resolver.strip()
        self.log = logger

        self.id = strip_DOI(doi)

        self._src = source
        self._cite = None
        self._data = None
        self._native = None

    @property
    def source(self):
        """
        the DOI registration agency that minted the DOI
        """
        return self._src

    @property
    def citation_text(self):
        """
        a formatted citation for the resource as recommended by the 
        registration agency.
        """
        if self._cite is None:
            self._cite = self._get_data(CT.citation_text, "text")
        return self._cite

    @property
    def data(self):
        """
        DOI metadata in a common schema (CSL Citation Styles).  The schema
        is the same regardless of the registration agency (e.g. DataCite, 
        Crossref)
        """
        if self._data is None:
            self._data = self._get_data(CT.Citeproc_JSON, "json")
        return self._data

    @property
    def native(self):
        """
        DOI metadata in the schema specific to the registration agency.  For
        example, a DataCite DOI will have data in the DataCite JSON metadata 
        sehema.  

        It is intended that the get method for this property would be
        overridden by a subclass implementation.
        """
        if self._native is None:
            self._native = {}
        return self._native

    def _get_data(self, cntntype, format="text"):
        hdrs = { "Accept": cntntype }
        url = self.resolver + self.id
        if self.log:
            self.log.debug("Requesting %s from %s", cntntype, url)

        # this may raise an exception
        try:
            resp = requests.get(url, headers=hdrs)
        except (requests.ConnectionError,
                requests.HTTPError,
                requests.ConnectTimeout)   as ex:
            raise DOICommunicationError(self.id, self.resolver, ex)
        except requests.RequestException as ex:
            raise DOIResolverError(self.id, self.resolver, cause=ex)
            
        if resp.status_code >= 200 and resp.status_code < 300:
            if format == "json":
                if resp.status_code == 204:   # No Content
                    return {}
                try:
                    return resp.json()
                except ValueError as ex:
                    raise DOIResolverError(self.id, self.resolver, cause=ex,
                                   message="Response is not parseable: "+str(ex))

            return resp.text
        
        if resp.status_code == 406:
            raise DOIUnsupportedContentType(cntntype, self.id, self.resolver)

        if resp.status_code == 404:
            raise DOIDoesNotExist(self.id, self.resolver)

        raise DOIResolverError(self.id, self.resolver,
                               resp.status_code, resp.reason)

class DOIResolutionException(Exception):
    """
    A base class for exceptions occurring while accessing DOIs and their 
    metadata
    """

    def __init__(self, message, doi=None, resolver=None, cause=None):
        """
        initialize the exception

        :param str message:  a message explaining the failure
        :param str doi:      the DOI that was being resolved
        :param Exception cause:  the underlying cause for the exception
        :param str resolver: the resolving service being accessed (usually)
                               in the form of a base URL
        """
        super(DOIResolutionException, self).__init__(message)
        self.doi = doi
        self.resolver = resolver
        self.cause = cause

class DOICommunicationError(DOIResolutionException):
    """
    An error that occurs while trying to establish a connection to or while 
    communicating with a DOI resolver service.  This is intended for errors
    that occur before the service is able to return legal response.
    """
    def __init__(self, doi=None, resolver=None, cause=None, message=None):
        """
        initialize the exception

        :param str doi:      the DOI that was being resolved
        :param str resolver: the resolving service being accessed (usually)
                               in the form of a base URL
        :param Exception cause:  the underlying cause for the exception
        :param str message:  a message explaining the failure; if not provided
                               a default one will be set based on cause
        """
        if not message:
            message = "Failure while communicating with DOI resolver"
            if resolver:
                message += " ({0})".format(resolver)
            if cause:
                message += ": " + str(cause)
        super(DOICommunicationError, self).__init__(message, doi, resolver,
                                                    cause)

class DOIResolverError(DOIResolutionException):
    """
    An error indicating an unexpected response or error status from a DOI 
    resolver service.
    """

    def __init__(self, doi=None, resolver=None, status=0, reason=None,
                 cause=None, message=None):
        """
        initialize the exception

        :param str doi:      the DOI that was being resolved
        :param str resolver: the resolving service being accessed (usually)
                               in the form of a base URL
        :param int status:   the HTTP status code returned from the resolver
        :param str reason:   the message returned from the resolver associated
                               with the status code
        :param Exception cause:  the underlying cause for the exception
        :param str message:  a message explaining the failure; if not provided
                               a default one will be set based on cause
        """
        if not message:
            message = "Unexpected resolution response"
            if doi:
                message += " for "+doi
            if reason:
                message += ": {0} ({1})".format(reason, status)
            elif cause:
                message += ": " + str(cause)
        
        super(DOIResolverError, self).__init__(message, doi, resolver, cause)
        self.status_code = status
        self.reason = reason

class DOIClientException(DOIResolutionException):
    """
    An exception during DOI resolution traceable to client input
    """
    def __init__(self, doi, resolver=None, message=None):
        """
        initialize the exception

        :param str doi:      the DOI that was being resolved
        :param str resolver: the resolving service being accessed (usually)
                               in the form of a base URL
        :param str message:  a message explaining the failure; if not provided
                               a default one will be set based on cause
        """
        if not message:
            message = "Unknown client error during DOI resolution of " + doi
        super(DOIClientException, self).__init__(message, doi, resolver)


class DOIDoesNotExist(DOIClientException):
    """
    An error indicating that a given DOI is unknown to the resolver
    """
    def __init__(self, doi, resolver=None, message=None):
        """
        initialize the exception

        :param str doi:      the DOI that was being resolved
        :param str resolver: the resolving service being accessed (usually)
                               in the form of a base URL
        :param str message:  a message explaining the failure; if not provided
                               a default one will be set based on cause
        """
        if not message:
            message = "DOI not found: " + doi
        super(DOIDoesNotExist, self).__init__(doi, resolver, message)

class DOIUnsupportedContentType(DOIClientException):
    """
    An error indicating that a given DOI is unknown to the resolver
    """
    def __init__(self, contenttype, doi=None, resolver=None, message=None):
        """
        initialize the exception

        :param str doi:      the DOI that was being resolved
        :param str resolver: the resolving service being accessed (usually)
                               in the form of a base URL
        :param str message:  a message explaining the failure; if not provided
                               a default one will be set based on cause
        """
        if not message:
            message = "Unsupported content type, " + contenttype
            if doi:
                message += ", for doi "+doi
        super(DOIUnsupportedContentType, self).__init__(doi, resolver, message)
        self.content_type = contenttype




                
        