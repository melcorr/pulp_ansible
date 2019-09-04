from collections import namedtuple
from gettext import gettext as _
import json
import re
import yaml

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from rest_framework.serializers import ValidationError
import semantic_version as semver
from yaml.error import YAMLError


CollectionFilename = namedtuple("CollectionFilename", ["namespace", "name", "version"])

FILENAME_RE = re.compile(
    r"^(?P<namespace>\w+)-(?P<name>\w+)-" r"(?P<version>[0-9a-zA-Z.+-]+)\.tar\.gz$"
)


def get_page_url(url, page=1):
    """Get URL page."""
    parsed_url = urlparse(url)
    new_query = parse_qs(parsed_url.query)
    new_query["page"] = page
    return urlunparse(parsed_url._replace(query=urlencode(new_query, doseq=True)))


def parse_metadata(download_result):
    """Parses JSON file."""
    with open(download_result.path) as fd:
        return json.load(fd)


def parse_collections_requirements_file(requirements_file_string):
    """
    Parses an Ansible requirement.yml file and returns all the collections defined in it.

    The requirements file is in the form:
        ---
        collections:
        - namespace.collection
        - name: namespace.collection
            version: version identifier, multiple identifiers are separated by ','
            source: the URL or prededefined source name in ~/.ansible_galaxy
                    to pull the collection from

    Args:
        requirements_file_string (str): The string of the requirements file.

    Returns:
        list: A list of tuples (name, version, source).

    Raises:
            rest_framework.serializers.ValidationError: if requirements is not a valid yaml.

    """
    collection_info = []

    if requirements_file_string:
        try:
            requirements = yaml.safe_load(requirements_file_string)
        except YAMLError as err:
            raise ValidationError(
                _(
                    "Failed to parse the collection requirements yml: {file} "
                    "with the following error: {error}".format(
                        file=requirements_file_string, error=err
                    )
                )
            )

        if not isinstance(requirements, dict) or "collections" not in requirements:
            raise ValidationError(
                _(
                    "Expecting collections requirements file to be a dict with the key "
                    "collections that contains a list of collections to install."
                )
            )

        for collection_req in requirements["collections"]:
            if isinstance(collection_req, dict):
                req_name = collection_req.get("name", None)
                if req_name is None:
                    raise ValidationError(
                        _("Collections requirement entry should contain the key name.")
                    )

                req_version = collection_req.get("version", "*")
                req_source = collection_req.get("source", None)

                collection_info.append((req_name, req_version, req_source))
            else:
                collection_info.append((collection_req, "*", None))

    return collection_info


def parse_collection_filename(filename):
    """
    Parses collection filename.

    Parses and validates collection filename. Returns CollectionFilename named tuple.
    Raises ValueError if filename is not a valid collection filename.
    """
    match = FILENAME_RE.match(filename)

    if not match:
        raise ValueError("Invalid filename. Expected: {namespace}-{name}-{version}.tar.gz")

    namespace, name, version = match.groups()
    # NOTE: Raises ValueError if version is invalid
    semver.Version.parse(version)

    return CollectionFilename(namespace, name, version)