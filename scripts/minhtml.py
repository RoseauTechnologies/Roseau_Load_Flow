# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "minify-html>=0.18.1",
# ]
# ///
import argparse
import sys

import minify_html


def main():
    parser = argparse.ArgumentParser(description="Minify HTML files.")
    parser.add_argument("html_files", nargs="+", help="HTML files to minify")
    parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite the original files with the minified content"
    )
    minify_html_group = parser.add_argument_group("minify-html options")
    minify_html_group.add_argument("--allow-noncompliant-unquoted-attribute-values", action="store_true")
    minify_html_group.add_argument("--allow-optimal-entities", action="store_true")
    minify_html_group.add_argument("--allow-removing-spaces-between-attributes", action="store_true")
    minify_html_group.add_argument("--keep-closing-tags", action="store_true")
    minify_html_group.add_argument("--keep-comments", action="store_true")
    minify_html_group.add_argument("--keep-html-and-head-opening-tags", action="store_true")
    minify_html_group.add_argument("--keep-input-type-text-attr", action="store_true")
    minify_html_group.add_argument("--keep-ssi-comments", action="store_true")
    minify_html_group.add_argument("--minify-css", action="store_true")
    minify_html_group.add_argument("--minify-doctype", action="store_true")
    minify_html_group.add_argument("--minify-js", action="store_true")
    minify_html_group.add_argument("--preserve-brace-template-syntax", action="store_true")
    minify_html_group.add_argument("--preserve-chevron-percent-template-syntax", action="store_true")
    minify_html_group.add_argument("--remove-bangs", action="store_true")
    minify_html_group.add_argument("--remove-processing-instructions", action="store_true")
    options = vars(parser.parse_args())
    html_files = options.pop("html_files")
    overwrite = options.pop("overwrite")
    exit_code = 0
    for html_file in html_files:
        with open(html_file, encoding="utf-8") as f:
            content = f.read()
        minified_content = minify_html.minify(content, **options)
        if not minified_content.endswith("\n"):
            minified_content += "\n"
        if minified_content != content:
            if overwrite:
                with open(html_file, "w", encoding="utf-8") as f:
                    f.write(minified_content)
            exit_code = 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
