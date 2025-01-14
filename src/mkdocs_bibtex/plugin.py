import re
from collections import OrderedDict
from pathlib import Path

from mkdocs.config import config_options
from mkdocs.plugins import BasePlugin
from pybtex.database import BibliographyData, parse_file

from mkdocs_bibtex.utils import (
    find_cite_keys,
    format_bibliography,
    format_pandoc,
    format_simple,
    insert_citation_keys,
)


class BibTexPlugin(BasePlugin):
    """
    Allows the use of bibtex in markdown content for MKDocs.

    Options:
        bib_file (string): path to a single bibtex file for entries
        bib_dir (string): path to a directory of bibtex files for entries
        bib_command (string): command to place a bibliography relevant to just that file
                              defaults to \bibliography
        full_bib_command (string): command to place a full bibliography of all references
        csl_file (string, optional): path to a CSL file, relative to mkdocs.yml.
    """

    config_scheme = [
        ("bib_file", config_options.File(exists=True, required=False)),
        ("bib_dir", config_options.Dir(exists=True, required=False)),
        ("bib_command", config_options.Type(str, default="\\bibliography")),
        ("full_bib_command", config_options.Type(str, default="\\full_bibliography")),
        ("csl_file", config_options.File(exists=True, required=False)),
    ]

    def __init__(self):
        self.bib_data = None
        self.all_references = OrderedDict()
        self.unescape_for_arithmatex = False

    def on_config(self, config):
        """
        Loads bibliography on load of config
        """

        bibfiles = []

        if self.config.get("bib_file", None) is not None:
            bibfiles.append(self.config["bib_file"])
        elif self.config.get("bib_dir", None) is not None:
            bibfiles.extend(Path(self.config["bib_dir"]).glob("*.bib"))
        else:
            raise Exception("Must supply a bibtex file or directory for bibtex files")

        # load bibliography data
        refs = {}
        for bibfile in bibfiles:
            bibdata = parse_file(bibfile)
            refs.update(bibdata.entries)

        self.bib_data = BibliographyData(entries=refs)

        self.csl_file = self.config.get("csl_file", None)

        return config

    def on_page_markdown(self, markdown, page, config, files):
        """
        Parses the markdown for each page, extracting the bibtex references
        If a local reference list is requested, this will render that list where requested

        1. Finds all cite keys (may include multiple citation references)
        2. Convert all cite keys to citation quads:
            (full cite key,
            induvidual cite key,
            citation key in corresponding style,
            citation for induvidual cite key)
        3. Insert formatted cite keys into text
        4. Insert the bibliography into the markdown
        5. Insert the full bibliograph into the markdown
        """

        # 1. Grab all the cited keys in the markdown
        cite_keys = find_cite_keys(markdown)

        # 2. Convert all the citations to text references
        citation_quads = self.format_citations(cite_keys)

        # 3. Insert in numbers into the main markdown and build bibliography
        markdown = insert_citation_keys(citation_quads, markdown)

        # 4. Insert in the bibliopgrahy text into the markdown
        bibliography = format_bibliography(citation_quads)
        markdown = re.sub(
            re.escape(self.config.get("bib_command", "\\bibliography")),
            bibliography,
            markdown,
        )

        # 5. Build the full Bibliography and insert into the text
        markdown = re.sub(
            re.escape(self.config.get("full_bib_command", "\\full_bibliography")),
            self.full_bibliography,
            markdown,
        )

        return markdown

    def format_citations(self, cite_keys):
        """
        Formats references into citation quads and adds them to the global registry

        Args:
            cite_keys (list): List of full cite_keys that maybe compound keys

        Returns:
            citation_quads: quad tupples of the citation inforamtion
        """

        # Deal with arithmatex fix at some point

        # 1. First collect any unformated references
        entries = {}
        for key_set in cite_keys:
            for key in key_set.strip().strip("]").strip("[").split(";"):
                key = key.strip().strip("@")
                if key not in self.all_references:
                    entries[key] = self.bib_data.entries[key]

        # 2. Format entries
        if self.csl_file:
            self.all_references.update(format_pandoc(entries, self.csl_file))
        else:
            self.all_references.update(format_simple(entries))

        # 3. Construct quads
        quads = []
        for key_set in cite_keys:
            for key in key_set.strip().strip("]").strip("[").split(";"):
                key = key.strip().strip("@")
                quads.append((key_set, key, "1", self.all_references[key]))

        return quads

    @property
    def full_bibliography(self):
        """
        Returns the full bibliography text
        """

        bibliography = []
        for number, (key, citation) in enumerate(self.all_references.items()):
            bibliography_text = "[^{}]: {}".format(number, citation)
            bibliography.append(bibliography_text)

        return "\n".join(bibliography)
