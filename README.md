# Pekosz Lab Nextstrain Builds

This repository houses all data for the [Pekosz Lab nextstrain builds](https://nextstrain.org/groups/PekoszLab) as well as  their required Nextclade datasets.

## How to upload an auspice build to the group: 

For detailed nextstrain group page settings and how to upload data, see the [Official Nextrain Documentation](https://docs.nextstrain.org/en/latest/guides/share/groups/index.html). 

### Login to nextstrain cli

```shell 
nextstrain login
```
### Add a pathogen workflow 

Replace `${YOUR_BUILD_NAME}` with the file name of the build. 

```shell
nextstrain remote upload \
    nextstrain.org/groups/PekoszLab/${YOUR_BUILD_NAME} \
    auspice/${YOUR_BUILD_NAME}.json
```

### Verify The Uploaded Build 

```shell
nextstrain remote list nextstrain.org/groups/PekoszLab
```
