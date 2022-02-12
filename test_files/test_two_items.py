import os

module_dir = os.path.dirname(os.path.abspath(__file__))
test_files_dir = os.path.abspath(os.path.join(module_dir, "..", "test_files"))

def test_on_2_items():
  plugin = BibTexPlugin()
  plugin.load_config(
        options={"bib_file": os.path.join(test_files_dir, "paper.bib")},
        config_file_path=None,
    )
  plugin.on_config(plugin.config)
  test_markdown = "Book of Why [@PM18] and Time Series Analysis [@Hamilton]\n\n \\bibliography"
  assert (
        "[^2]:" in plugin.on_page_markdown(test_markdown, None, None, None)
    )
