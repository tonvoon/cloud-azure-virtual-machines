# CDs to an opspack's plugins directory, builds the go sources and shouts the list of executables
define build_go_sources
cd $(1)/plugins && \
go build -ldflags "-s -w" -v *.go
endef

# Remove all go files in the given opspack folder
define remove_go_sources
cd $(1)/plugins && \
rm *.go
endef

# CDs to an opspack's plugins directory, pre-processes the ps1 sources and shouts the list of executables
define ps1_preprocess
$(foreach f,$(call ps1_sources,$(1)),$(call ps1_preprocess_file,$(f)))
endef

# Gets the .ps1 sources for an opspack. Suppresses errors for missing /plugins dirs.
define ps1_sources
$(shell find $(1)/plugins -name '*.ps1' -and \( -type f -or -type l \) 2>/dev/null || true)
endef

# Runs the ps1 preprocess script for the given file
define ps1_preprocess_file
${CWD}/utils/ps1-preprocess.pl $(1)
endef

define view_files
ls -l
endef

view_directory:
	ls -l

create_opspack:
	go get github.com/opsview/go-plugin

	$(call build_go_sources,$$OPSPACK_NAME) || $(call view_files)

	$(call remove_go_sources,$$OPSPACK_NAME) || $(call view_files)

#	$(call ps1_preprocess,$$OPSPACK_NAME) || $(call view_files) TODO

	ls -l $$OPSPACK_NAME/plugins
	tar -zcvf $$OPSPACK_NAME.opspack $$OPSPACK_NAME