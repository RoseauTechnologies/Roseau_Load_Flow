# Makefile to generate the LaTeX figures

# Programs
LUALATEX:=$(shell which lualatex)
PDF2SVG:=$(shell which pdf2svg)
SVGO:=$(shell which svgo)

# Folders
INPUT_FOLDER:=$(shell realpath .)
BUILD_FOLDER:=$(INPUT_FOLDER)/_build
OUTPUT_FOLDER:=$(shell realpath ../_static/)

# Files
COMMON_TEX_FILES:=Preamble.tex Load/FlexibleLoad/Domain_Common.tex Transformer/Windings_Common.tex Transformer/Connection_Defs.tex
TEX_FILES:=$(filter-out $(COMMON_TEX_FILES), $(shell find . -name '*.tex' -type f -not -path './_build/*' | sed -r 's/^\.\///'))
PDF_FILES:=$(TEX_FILES:%.tex=$(BUILD_FOLDER)/%.pdf)
DEP_FILES:=$(TEX_FILES:%.tex=$(BUILD_FOLDER)/%.d)
SVG_FILES:=$(TEX_FILES:%.tex=$(OUTPUT_FOLDER)/%.svg)
# The dependencies of these PDF files are unknown, they must be compiled at least once
UNKNOWN_DEP_PDF_FILES:=$(patsubst %.d,%.pdf,$(filter-out $(wildcard $(DEP_FILES)),$(DEP_FILES)))


# Rules
.PHONY: all clean cleanall checks FORCE

# Keep the PDF files in the build folder to be able to inspect them
.SECONDARY: $(PDF_FILES)

all: $(SVG_FILES)

# The PDF files are compiled with the `--recorder` option which lists all the files read by LuaLaTeX
# in a `.fls` file. The local files (sources, preamble, CSV data, etc.) are written as dependencies
# of the PDF file in a `.d` file, which is included below. An empty rule is added for each dependency
# so that deleting or renaming a file does not break the build.
$(BUILD_FOLDER)/%.pdf: %.tex | checks
	@mkdir -p $(@D)
	@$(LUALATEX) --jobname=$* --file-line-error --interaction=nonstopmode --halt-on-error \
	--recorder --output-directory=$(BUILD_FOLDER) $<
	@deps=$$(sed -n 's/^INPUT \.\///p' $(@:.pdf=.fls) | sort -u | tr '\n' ' '); \
	{ echo "$@: $$deps"; for dep in $$deps; do echo "$$dep:"; done; } > $(@:.pdf=.d)

$(OUTPUT_FOLDER)/%.svg: $(BUILD_FOLDER)/%.pdf
	@mkdir -p $(@D)
	@$(PDF2SVG) $< $@
	@$(SVGO) --multipass --final-newline $@

-include $(DEP_FILES)
$(UNKNOWN_DEP_PDF_FILES): FORCE

clean:
	@rm -rf $(BUILD_FOLDER) *~
	@find $(INPUT_FOLDER) -type f \( -name '*.aux' -o -name '*.log' -o -name '*.pdf' \
	-o -name '*.fls' -o -name '*.fdb_latexmk' -o -name '*.synctex.gz' \) -delete

cleanall: clean
	@rm -f $(SVG_FILES)

checks:
	@status=0; \
	if [ -z "$(LUALATEX)" ]; then \
		echo "LuaLaTeX is required to compile the figures! https://yihui.org/tinytex/"; status=1; \
	fi; \
	if [ -z "$(PDF2SVG)" ]; then \
		echo "Pdf2svg is required to compile the figures! https://github.com/dawbarton/pdf2svg"; status=1; \
	fi; \
	if [ -z "$(SVGO)" ]; then \
		echo "Svgo is required to compile the figures! https://github.com/svg/svgo"; status=1; \
	fi; \
	exit $$status

# Local Variables:
# mode: makefile-gmake
# coding: utf-8-unix
# fill-column: 100
# End:
