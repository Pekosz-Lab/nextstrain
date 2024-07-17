# Pekosz Lab Nextstrain Builds

This repository houses all configuration data and **WORKING** scripts for the [Pekosz Lab nextstrain builds](https://nextstrain.org/groups/PekoszLab) as well as their required Nextclade datasets. Currently, 2 types of datasets are regularly maintained: 

1. 24 [Seasonal Influenza Genome Builds](seasonal-flu/) (H1N1, H3N2, and B/Vic) of circulaing viruses detected through the Johns Hopkins Hospital Network supported by [JH-CEIRR](https://www.ceirr-network.org/centers/jh-ceirr).

2. Specialized Builds Unique to Pekosz Lab-specific manuscripts.

> [!IMPORTANT] 🚧
> This repository is under construction thus scripts are not constructed for optimal run efficiency.

## How to upload an auspice build to the group (example): 

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
