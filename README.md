# About
Tool for convert raw item data from [Guns Girl - Houkai Gakuen 2](https://houkai2nd.miraheze.org/wiki/Houkai_Gakuen_2_Wiki) into displayable info

# Usage
Download data_all using [hg2-downloader](https://dev.s-ul.net/BLUEALiCE/hg2-downloader)

Extract TextAssets from it using [AssetStudio](https://github.com/Perfare/AssetStudio)

Put data into data/JP or data/CN folder (Based from where you have downloaded data)

Use getters functions in main.py to extract info

# Comparison with [redbean-parser](https://github.com/quinckky/hg2-redbean-item-parser)

+ Faster
+ You can avoid most of typos (Sometimes mihoyo typos just not avoidable)
+ Flexible (You can edit code to parse additional data)
- Need to work with AssetBundles
