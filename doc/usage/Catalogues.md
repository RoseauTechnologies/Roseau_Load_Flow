# Catalogues

In _Roseau Load Flow_, some classes are provided with a catalogue. This page describes how to use them.

(catalogues-networks)=

## Networks

_Roseau Load Flow_ is provided with a small catalogue of MV and LV networks. These networks are available through
the class `ElectricalNetwork`.

Here is an interactive plot to explore them. See the [Plotting page](./Plotting.md) to learn how to get such
interactive map.

<iframe src="../_static/Network/Catalogue.html" height="600px" width="100%" frameborder="0"></iframe>

### Source of data

All these networks are built from open data available in France. The entire France can be provided on demand. Please
email us at [contact@roseautechnologies.com](mailto:contact@roseautechnologies.com).

### Inspecting the catalogue

This catalogue can be retrieved in the form of a dataframe using:

```pycon
>>> from roseau.load_flow import ElectricalNetwork
>>> ElectricalNetwork.get_catalogue()
```

| Name                                                                              | Nb buses | Nb branches | Nb loads | Nb sources | Nb grounds | Nb potential refs | Available load points |
| :-------------------------------------------------------------------------------- | -------: | ----------: | -------: | ---------: | ---------: | ----------------: | :-------------------- |
| <a href="../_static/Network/LVFeeder00939.html" target="_blank">LVFeeder00939</a> |        8 |           7 |       12 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/LVFeeder02639.html" target="_blank">LVFeeder02639</a> |        7 |           6 |       10 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/LVFeeder04790.html" target="_blank">LVFeeder04790</a> |        4 |           3 |        4 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/LVFeeder06713.html" target="_blank">LVFeeder06713</a> |        3 |           2 |        2 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/LVFeeder06926.html" target="_blank">LVFeeder06926</a> |        3 |           2 |        2 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/LVFeeder06975.html" target="_blank">LVFeeder06975</a> |        6 |           5 |        8 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/LVFeeder18498.html" target="_blank">LVFeeder18498</a> |       18 |          17 |       32 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/LVFeeder18769.html" target="_blank">LVFeeder18769</a> |        7 |           6 |       10 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/LVFeeder19558.html" target="_blank">LVFeeder19558</a> |        3 |           2 |        2 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/LVFeeder20256.html" target="_blank">LVFeeder20256</a> |        9 |           8 |       14 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/LVFeeder23832.html" target="_blank">LVFeeder23832</a> |        3 |           2 |        2 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/LVFeeder24400.html" target="_blank">LVFeeder24400</a> |        4 |           3 |        4 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/LVFeeder27429.html" target="_blank">LVFeeder27429</a> |       11 |          10 |       18 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/LVFeeder27681.html" target="_blank">LVFeeder27681</a> |        3 |           2 |        2 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/LVFeeder30216.html" target="_blank">LVFeeder30216</a> |        9 |           8 |       14 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/LVFeeder31441.html" target="_blank">LVFeeder31441</a> |        4 |           3 |        4 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/LVFeeder36284.html" target="_blank">LVFeeder36284</a> |        5 |           4 |        6 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/LVFeeder36360.html" target="_blank">LVFeeder36360</a> |        9 |           8 |       14 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/LVFeeder37263.html" target="_blank">LVFeeder37263</a> |        3 |           2 |        2 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/LVFeeder38211.html" target="_blank">LVFeeder38211</a> |        6 |           5 |        8 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/MVFeeder004.html" target="_blank">MVFeeder004</a>     |       17 |          16 |       10 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/MVFeeder011.html" target="_blank">MVFeeder011</a>     |       50 |          49 |       68 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/MVFeeder015.html" target="_blank">MVFeeder015</a>     |       30 |          29 |       20 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/MVFeeder032.html" target="_blank">MVFeeder032</a>     |       53 |          52 |       40 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/MVFeeder041.html" target="_blank">MVFeeder041</a>     |       88 |          87 |       62 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/MVFeeder063.html" target="_blank">MVFeeder063</a>     |       39 |          38 |       38 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/MVFeeder078.html" target="_blank">MVFeeder078</a>     |       69 |          68 |       46 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/MVFeeder115.html" target="_blank">MVFeeder115</a>     |        4 |           3 |        4 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/MVFeeder128.html" target="_blank">MVFeeder128</a>     |       49 |          48 |       32 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/MVFeeder151.html" target="_blank">MVFeeder151</a>     |       59 |          58 |       44 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/MVFeeder159.html" target="_blank">MVFeeder159</a>     |        8 |           7 |        0 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/MVFeeder176.html" target="_blank">MVFeeder176</a>     |       33 |          32 |       20 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/MVFeeder210.html" target="_blank">MVFeeder210</a>     |      128 |         127 |       82 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/MVFeeder217.html" target="_blank">MVFeeder217</a>     |       44 |          43 |       44 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/MVFeeder232.html" target="_blank">MVFeeder232</a>     |       66 |          65 |       38 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/MVFeeder251.html" target="_blank">MVFeeder251</a>     |      125 |         124 |      106 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/MVFeeder290.html" target="_blank">MVFeeder290</a>     |       12 |          11 |       16 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/MVFeeder312.html" target="_blank">MVFeeder312</a>     |       11 |          10 |        8 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/MVFeeder320.html" target="_blank">MVFeeder320</a>     |       20 |          19 |       12 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| <a href="../_static/Network/MVFeeder339.html" target="_blank">MVFeeder339</a>     |       33 |          32 |       28 |          1 |          1 |                 1 | 'Summer', 'Winter'    |

There are MV networks whose names start with "MVFeeder" and LV networks whose names with "LVFeeder". For each
network, there are two available load points:

- "Winter": it contains power loads without production.
- "Summer": it contains power loads with production and 20% of the "Winter" load.

The arguments of the method `get_catalogue` can be used to filter the output. If you want to get the LV networks
only, you can call:

```pycon
>>> ElectricalNetwork.get_catalogue(name="LVFeeder")
```

| Name          | Nb buses | Nb branches | Nb loads | Nb sources | Nb grounds | Nb potential refs | Available load points |
| :------------ | -------: | ----------: | -------: | ---------: | ---------: | ----------------: | :-------------------- |
| LVFeeder00939 |        8 |           7 |       12 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| LVFeeder02639 |        7 |           6 |       10 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| LVFeeder04790 |        4 |           3 |        4 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| LVFeeder06713 |        3 |           2 |        2 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| LVFeeder06926 |        3 |           2 |        2 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| LVFeeder06975 |        6 |           5 |        8 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| LVFeeder18498 |       18 |          17 |       32 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| LVFeeder18769 |        7 |           6 |       10 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| LVFeeder19558 |        3 |           2 |        2 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| LVFeeder20256 |        9 |           8 |       14 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| LVFeeder23832 |        3 |           2 |        2 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| LVFeeder24400 |        4 |           3 |        4 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| LVFeeder27429 |       11 |          10 |       18 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| LVFeeder27681 |        3 |           2 |        2 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| LVFeeder30216 |        9 |           8 |       14 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| LVFeeder31441 |        4 |           3 |        4 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| LVFeeder36284 |        5 |           4 |        6 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| LVFeeder36360 |        9 |           8 |       14 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| LVFeeder37263 |        3 |           2 |        2 |          1 |          1 |                 1 | 'Summer', 'Winter'    |
| LVFeeder38211 |        6 |           5 |        8 |          1 |          1 |                 1 | 'Summer', 'Winter'    |

A regular expression can also be used:

```pycon
>>> ElectricalNetwork.get_catalogue(name=r"LVFeeder38[0-9]+")
```

| Name          | Nb buses | Nb branches | Nb loads | Nb sources | Nb grounds | Nb potential refs | Available load points |
| :------------ | -------: | ----------: | -------: | ---------: | ---------: | ----------------: | :-------------------- |
| LVFeeder38211 |        6 |           5 |        8 |          1 |          1 |                 1 | 'Summer', 'Winter'    |

### Getting an instance

You can build an `ElectricalNetwork` instance from the catalogue using the class method
`from_catalogue`. The name of the network and the name of the load point must be provided:

```pycon
>>> en = ElectricalNetwork.from_catalogue(name="LVFeeder38211", load_point_name="Summer")
<ElectricalNetwork: 6 buses, 5 branches, 8 loads, 1 source, 1 ground, 1 potential ref>
```

In case no or several results match the parameters, an error is raised:

```pycon
>>> ElectricalNetwork.from_catalogue(name="LVFeeder38211", load_point_name="Unknown")
RoseauLoadFlowException: No load points for network 'LVFeeder38211' matching the query (load_point_name='Unknown')
have been found. Please look at the catalogue using the `get_catalogue` class method. [catalogue_not_found]
```

(catalogues-transformers)=

## Transformers

_Roseau Load Flow_ is provided with a catalogue of transformer parameters. These parameters are available
through the class `TransformerParameters`.

```{note}
Currently, only three phase MV/LV transformers are in the catalogue.
```

### Source of data

The available transformers data come from the following data sheets:

- For Schneider-Electric: [here](../_static/Transformer/2023_03_31_Fiche_Technique_Schneider_Electric.pdf) on page
  19, 21 and 22.
- For France Transfo: [here](../_static/Transformer/2023_03_30_Fiche_Technique_France_Transfo.pdf).

Pull requests to add some other sources are welcome!

### Inspecting the catalogue

This catalogue can be retrieved in the form of a dataframe using:

```pycon
>>> from roseau.load_flow import TransformerParameters
>>> TransformerParameters.get_catalogue()
```

| Id                                     | Manufacturer | Product range | Efficiency           | Type  | Nominal power (kVA) | High voltage (kV) | Low voltage (kV) |
| :------------------------------------- | :----------- | :------------ | :------------------- | :---- | ------------------: | ----------------: | ---------------: |
| FT_Standard_Standard_100kVA            | FT           | Standard      | Standard             | Dyn11 |               100.0 |              20.0 |              0.4 |
| FT_Standard_Standard_160kVA            | FT           | Standard      | Standard             | Dyn11 |               160.0 |              20.0 |              0.4 |
| FT_Standard_Standard_250kVA            | FT           | Standard      | Standard             | Dyn11 |               250.0 |              20.0 |              0.4 |
| FT_Standard_Standard_315kVA            | FT           | Standard      | Standard             | Dyn11 |               315.0 |              20.0 |              0.4 |
| FT_Standard_Standard_400kVA            | FT           | Standard      | Standard             | Dyn11 |               400.0 |              20.0 |              0.4 |
| FT_Standard_Standard_500kVA            | FT           | Standard      | Standard             | Dyn11 |               500.0 |              20.0 |              0.4 |
| FT_Standard_Standard_630kVA            | FT           | Standard      | Standard             | Dyn11 |               630.0 |              20.0 |              0.4 |
| FT_Standard_Standard_800kVA            | FT           | Standard      | Standard             | Dyn11 |               800.0 |              20.0 |              0.4 |
| FT_Standard_Standard_1000kVA           | FT           | Standard      | Standard             | Dyn11 |              1000.0 |              20.0 |              0.4 |
| FT_Standard_Standard_1250kVA           | FT           | Standard      | Standard             | Dyn11 |              1250.0 |              20.0 |              0.4 |
| FT_Standard_Standard_1600kVA           | FT           | Standard      | Standard             | Dyn11 |              1600.0 |              20.0 |              0.4 |
| FT_Standard_Standard_2000kVA           | FT           | Standard      | Standard             | Dyn11 |              2000.0 |              20.0 |              0.4 |
| FT_Standard_Standard_2500kVA           | FT           | Standard      | Standard             | Dyn11 |              2500.0 |              20.0 |              0.4 |
| FT_Standard_Standard_3150kVA           | FT           | Standard      | Standard             | Dyn11 |              3150.0 |              20.0 |              0.4 |
| SE_Minera_A0Ak_50kVA                   | SE           | Minera        | A0Ak                 | Yzn11 |                50.0 |              20.0 |              0.4 |
| SE_Minera_A0Ak_100kVA                  | SE           | Minera        | A0Ak                 | Dyn11 |               100.0 |              20.0 |              0.4 |
| SE_Minera_A0Ak_160kVA                  | SE           | Minera        | A0Ak                 | Dyn11 |               160.0 |              20.0 |              0.4 |
| SE_Minera_A0Ak_250kVA                  | SE           | Minera        | A0Ak                 | Dyn11 |               250.0 |              20.0 |              0.4 |
| SE_Minera_A0Ak_315kVA                  | SE           | Minera        | A0Ak                 | Dyn11 |               315.0 |              20.0 |              0.4 |
| SE_Minera_A0Ak_400kVA                  | SE           | Minera        | A0Ak                 | Dyn11 |               400.0 |              20.0 |              0.4 |
| SE_Minera_A0Ak_500kVA                  | SE           | Minera        | A0Ak                 | Dyn11 |               500.0 |              20.0 |              0.4 |
| SE_Minera_A0Ak_630kVA                  | SE           | Minera        | A0Ak                 | Dyn11 |               630.0 |              20.0 |              0.4 |
| SE_Minera_A0Ak_800kVA                  | SE           | Minera        | A0Ak                 | Dyn11 |               800.0 |              20.0 |              0.4 |
| SE_Minera_A0Ak_1000kVA                 | SE           | Minera        | A0Ak                 | Dyn11 |              1000.0 |              20.0 |              0.4 |
| SE_Minera_A0Ak_1250kVA                 | SE           | Minera        | A0Ak                 | Dyn11 |              1250.0 |              20.0 |              0.4 |
| SE_Minera_A0Ak_1600kVA                 | SE           | Minera        | A0Ak                 | Dyn11 |              1600.0 |              20.0 |              0.4 |
| SE_Minera_A0Ak_2000kVA                 | SE           | Minera        | A0Ak                 | Dyn11 |              2000.0 |              20.0 |              0.4 |
| SE_Minera_A0Ak_2500kVA                 | SE           | Minera        | A0Ak                 | Dyn11 |              2500.0 |              20.0 |              0.4 |
| SE_Minera_B0Bk_50kVA                   | SE           | Minera        | B0Bk                 | Yzn11 |                50.0 |              20.0 |              0.4 |
| SE_Minera_B0Bk_100kVA                  | SE           | Minera        | B0Bk                 | Dyn11 |               100.0 |              20.0 |              0.4 |
| SE_Minera_B0Bk_160kVA                  | SE           | Minera        | B0Bk                 | Dyn11 |               160.0 |              20.0 |              0.4 |
| SE_Minera_B0Bk_250kVA                  | SE           | Minera        | B0Bk                 | Dyn11 |               250.0 |              20.0 |              0.4 |
| SE_Minera_B0Bk_315kVA                  | SE           | Minera        | B0Bk                 | Dyn11 |               315.0 |              20.0 |              0.4 |
| SE_Minera_B0Bk_400kVA                  | SE           | Minera        | B0Bk                 | Dyn11 |               400.0 |              20.0 |              0.4 |
| SE_Minera_B0Bk_500kVA                  | SE           | Minera        | B0Bk                 | Dyn11 |               500.0 |              20.0 |              0.4 |
| SE_Minera_B0Bk_630kVA                  | SE           | Minera        | B0Bk                 | Dyn11 |               630.0 |              20.0 |              0.4 |
| SE_Minera_B0Bk_800kVA                  | SE           | Minera        | B0Bk                 | Dyn11 |               800.0 |              20.0 |              0.4 |
| SE_Minera_B0Bk_1000kVA                 | SE           | Minera        | B0Bk                 | Dyn11 |              1000.0 |              20.0 |              0.4 |
| SE_Minera_B0Bk_1250kVA                 | SE           | Minera        | B0Bk                 | Dyn11 |              1250.0 |              20.0 |              0.4 |
| SE_Minera_B0Bk_1600kVA                 | SE           | Minera        | B0Bk                 | Dyn11 |              1600.0 |              20.0 |              0.4 |
| SE_Minera_B0Bk_2000kVA                 | SE           | Minera        | B0Bk                 | Dyn11 |              2000.0 |              20.0 |              0.4 |
| SE_Minera_B0Bk_2500kVA                 | SE           | Minera        | B0Bk                 | Dyn11 |              2500.0 |              20.0 |              0.4 |
| SE_Minera_C0Bk_50kVA                   | SE           | Minera        | C0Bk                 | Yzn11 |                50.0 |              20.0 |              0.4 |
| SE_Minera_C0Bk_100kVA                  | SE           | Minera        | C0Bk                 | Dyn11 |               100.0 |              20.0 |              0.4 |
| SE_Minera_C0Bk_160kVA                  | SE           | Minera        | C0Bk                 | Dyn11 |               160.0 |              20.0 |              0.4 |
| SE_Minera_C0Bk_250kVA                  | SE           | Minera        | C0Bk                 | Dyn11 |               250.0 |              20.0 |              0.4 |
| SE_Minera_C0Bk_315kVA                  | SE           | Minera        | C0Bk                 | Dyn11 |               315.0 |              20.0 |              0.4 |
| SE_Minera_C0Bk_400kVA                  | SE           | Minera        | C0Bk                 | Dyn11 |               400.0 |              20.0 |              0.4 |
| SE_Minera_C0Bk_500kVA                  | SE           | Minera        | C0Bk                 | Dyn11 |               500.0 |              20.0 |              0.4 |
| SE_Minera_C0Bk_630kVA                  | SE           | Minera        | C0Bk                 | Dyn11 |               630.0 |              20.0 |              0.4 |
| SE_Minera_C0Bk_800kVA                  | SE           | Minera        | C0Bk                 | Dyn11 |               800.0 |              20.0 |              0.4 |
| SE_Minera_C0Bk_1000kVA                 | SE           | Minera        | C0Bk                 | Dyn11 |              1000.0 |              20.0 |              0.4 |
| SE_Minera_C0Bk_1250kVA                 | SE           | Minera        | C0Bk                 | Dyn11 |              1250.0 |              20.0 |              0.4 |
| SE_Minera_C0Bk_1600kVA                 | SE           | Minera        | C0Bk                 | Dyn11 |              1600.0 |              20.0 |              0.4 |
| SE_Minera_C0Bk_2000kVA                 | SE           | Minera        | C0Bk                 | Dyn11 |              2000.0 |              20.0 |              0.4 |
| SE_Minera_C0Bk_2500kVA                 | SE           | Minera        | C0Bk                 | Dyn11 |              2500.0 |              20.0 |              0.4 |
| SE_Minera_Standard_50kVA               | SE           | Minera        | Standard             | Yzn11 |                50.0 |              20.0 |              0.4 |
| SE_Minera_Standard_100kVA              | SE           | Minera        | Standard             | Dyn11 |               100.0 |              20.0 |              0.4 |
| SE_Minera_Standard_160kVA              | SE           | Minera        | Standard             | Dyn11 |               160.0 |              20.0 |              0.4 |
| SE_Minera_Standard_250kVA              | SE           | Minera        | Standard             | Dyn11 |               250.0 |              20.0 |              0.4 |
| SE_Minera_Standard_315kVA              | SE           | Minera        | Standard             | Dyn11 |               315.0 |              20.0 |              0.4 |
| SE_Minera_Standard_400kVA              | SE           | Minera        | Standard             | Dyn11 |               400.0 |              20.0 |              0.4 |
| SE_Minera_Standard_500kVA              | SE           | Minera        | Standard             | Dyn11 |               500.0 |              20.0 |              0.4 |
| SE_Minera_Standard_630kVA              | SE           | Minera        | Standard             | Dyn11 |               630.0 |              20.0 |              0.4 |
| SE_Minera_Standard_800kVA              | SE           | Minera        | Standard             | Dyn11 |               800.0 |              20.0 |              0.4 |
| SE_Minera_Standard_1000kVA             | SE           | Minera        | Standard             | Dyn11 |              1000.0 |              20.0 |              0.4 |
| SE_Minera_Standard_1250kVA             | SE           | Minera        | Standard             | Dyn11 |              1250.0 |              20.0 |              0.4 |
| SE_Minera_Standard_1600kVA             | SE           | Minera        | Standard             | Dyn11 |              1600.0 |              20.0 |              0.4 |
| SE_Minera_Standard_2000kVA             | SE           | Minera        | Standard             | Dyn11 |              2000.0 |              20.0 |              0.4 |
| SE_Minera_Standard_2500kVA             | SE           | Minera        | Standard             | Dyn11 |              2500.0 |              20.0 |              0.4 |
| SE_Trihal_Extra_Reduced_Losses_160kVA  | SE           | Trihal        | Extra_Reduced_Losses | Dyn11 |               160.0 |              20.0 |              0.4 |
| SE_Trihal_Extra_Reduced_Losses_250kVA  | SE           | Trihal        | Extra_Reduced_Losses | Dyn11 |               250.0 |              20.0 |              0.4 |
| SE_Trihal_Extra_Reduced_Losses_400kVA  | SE           | Trihal        | Extra_Reduced_Losses | Dyn11 |               400.0 |              20.0 |              0.4 |
| SE_Trihal_Extra_Reduced_Losses_630kVA  | SE           | Trihal        | Extra_Reduced_Losses | Dyn11 |               630.0 |              20.0 |              0.4 |
| SE_Trihal_Extra_Reduced_Losses_800kVA  | SE           | Trihal        | Extra_Reduced_Losses | Dyn11 |               800.0 |              20.0 |              0.4 |
| SE_Trihal_Extra_Reduced_Losses_1000kVA | SE           | Trihal        | Extra_Reduced_Losses | Dyn11 |              1000.0 |              20.0 |              0.4 |
| SE_Trihal_Extra_Reduced_Losses_1250kVA | SE           | Trihal        | Extra_Reduced_Losses | Dyn11 |              1250.0 |              20.0 |              0.4 |
| SE_Trihal_Extra_Reduced_Losses_1600kVA | SE           | Trihal        | Extra_Reduced_Losses | Dyn11 |              1600.0 |              20.0 |              0.4 |
| SE_Trihal_Extra_Reduced_Losses_2000kVA | SE           | Trihal        | Extra_Reduced_Losses | Dyn11 |              2000.0 |              20.0 |              0.4 |
| SE_Trihal_Extra_Reduced_Losses_2500kVA | SE           | Trihal        | Extra_Reduced_Losses | Dyn11 |              2500.0 |              20.0 |              0.4 |
| SE_Trihal_Reduced_Losses_160kVA        | SE           | Trihal        | Reduced_Losses       | Dyn11 |               160.0 |              20.0 |              0.4 |
| SE_Trihal_Reduced_Losses_250kVA        | SE           | Trihal        | Reduced_Losses       | Dyn11 |               250.0 |              20.0 |              0.4 |
| SE_Trihal_Reduced_Losses_400kVA        | SE           | Trihal        | Reduced_Losses       | Dyn11 |               400.0 |              20.0 |              0.4 |
| SE_Trihal_Reduced_Losses_630kVA        | SE           | Trihal        | Reduced_Losses       | Dyn11 |               630.0 |              20.0 |              0.4 |
| SE_Trihal_Reduced_Losses_800kVA        | SE           | Trihal        | Reduced_Losses       | Dyn11 |               800.0 |              20.0 |              0.4 |
| SE_Trihal_Reduced_Losses_1000kVA       | SE           | Trihal        | Reduced_Losses       | Dyn11 |              1000.0 |              20.0 |              0.4 |
| SE_Trihal_Reduced_Losses_1250kVA       | SE           | Trihal        | Reduced_Losses       | Dyn11 |              1250.0 |              20.0 |              0.4 |
| SE_Trihal_Reduced_Losses_1600kVA       | SE           | Trihal        | Reduced_Losses       | Dyn11 |              1600.0 |              20.0 |              0.4 |
| SE_Trihal_Reduced_Losses_2000kVA       | SE           | Trihal        | Reduced_Losses       | Dyn11 |              2000.0 |              20.0 |              0.4 |
| SE_Trihal_Reduced_Losses_2500kVA       | SE           | Trihal        | Reduced_Losses       | Dyn11 |              2500.0 |              20.0 |              0.4 |
| SE_Trihal_Standard_160kVA              | SE           | Trihal        | Standard             | Dyn11 |               160.0 |              20.0 |              0.4 |
| SE_Trihal_Standard_250kVA              | SE           | Trihal        | Standard             | Dyn11 |               250.0 |              20.0 |              0.4 |
| SE_Trihal_Standard_400kVA              | SE           | Trihal        | Standard             | Dyn11 |               400.0 |              20.0 |              0.4 |
| SE_Trihal_Standard_630kVA              | SE           | Trihal        | Standard             | Dyn11 |               630.0 |              20.0 |              0.4 |
| SE_Trihal_Standard_800kVA              | SE           | Trihal        | Standard             | Dyn11 |               800.0 |              20.0 |              0.4 |
| SE_Trihal_Standard_1000kVA             | SE           | Trihal        | Standard             | Dyn11 |              1000.0 |              20.0 |              0.4 |
| SE_Trihal_Standard_1250kVA             | SE           | Trihal        | Standard             | Dyn11 |              1250.0 |              20.0 |              0.4 |
| SE_Trihal_Standard_1600kVA             | SE           | Trihal        | Standard             | Dyn11 |              1600.0 |              20.0 |              0.4 |
| SE_Trihal_Standard_2000kVA             | SE           | Trihal        | Standard             | Dyn11 |              2000.0 |              20.0 |              0.4 |
| SE_Trihal_Standard_2500kVA             | SE           | Trihal        | Standard             | Dyn11 |              2500.0 |              20.0 |              0.4 |
| SE_Vegeta_C0Bk_50kVA                   | SE           | Vegeta        | C0Bk                 | Dyn11 |                50.0 |              20.0 |              0.4 |
| SE_Vegeta_C0Bk_100kVA                  | SE           | Vegeta        | C0Bk                 | Dyn11 |               100.0 |              20.0 |              0.4 |
| SE_Vegeta_C0Bk_160kVA                  | SE           | Vegeta        | C0Bk                 | Dyn11 |               160.0 |              20.0 |              0.4 |
| SE_Vegeta_C0Bk_250kVA                  | SE           | Vegeta        | C0Bk                 | Dyn11 |               250.0 |              20.0 |              0.4 |
| SE_Vegeta_C0Bk_315kVA                  | SE           | Vegeta        | C0Bk                 | Dyn11 |               315.0 |              20.0 |              0.4 |
| SE_Vegeta_C0Bk_400kVA                  | SE           | Vegeta        | C0Bk                 | Dyn11 |               400.0 |              20.0 |              0.4 |
| SE_Vegeta_C0Bk_500kVA                  | SE           | Vegeta        | C0Bk                 | Dyn11 |               500.0 |              20.0 |              0.4 |
| SE_Vegeta_C0Bk_630kVA                  | SE           | Vegeta        | C0Bk                 | Dyn11 |               630.0 |              20.0 |              0.4 |
| SE_Vegeta_C0Bk_800kVA                  | SE           | Vegeta        | C0Bk                 | Dyn11 |               800.0 |              20.0 |              0.4 |
| SE_Vegeta_C0Bk_1000kVA                 | SE           | Vegeta        | C0Bk                 | Dyn11 |              1000.0 |              20.0 |              0.4 |
| SE_Vegeta_C0Bk_1250kVA                 | SE           | Vegeta        | C0Bk                 | Dyn11 |              1250.0 |              20.0 |              0.4 |
| SE_Vegeta_C0Bk_1600kVA                 | SE           | Vegeta        | C0Bk                 | Dyn11 |              1600.0 |              20.0 |              0.4 |
| SE_Vegeta_C0Bk_2000kVA                 | SE           | Vegeta        | C0Bk                 | Dyn11 |              2000.0 |              20.0 |              0.4 |
| SE_Vegeta_C0Bk_2500kVA                 | SE           | Vegeta        | C0Bk                 | Dyn11 |              2500.0 |              20.0 |              0.4 |
| SE_Vegeta_C0Bk_3150kVA                 | SE           | Vegeta        | C0Bk                 | Dyn11 |              3150.0 |              20.0 |              0.4 |
| SE_Vegeta_Standard_50kVA               | SE           | Vegeta        | Standard             | Dyn11 |                50.0 |              20.0 |              0.4 |
| SE_Vegeta_Standard_100kVA              | SE           | Vegeta        | Standard             | Dyn11 |               100.0 |              20.0 |              0.4 |
| SE_Vegeta_Standard_160kVA              | SE           | Vegeta        | Standard             | Dyn11 |               160.0 |              20.0 |              0.4 |
| SE_Vegeta_Standard_250kVA              | SE           | Vegeta        | Standard             | Dyn11 |               250.0 |              20.0 |              0.4 |
| SE_Vegeta_Standard_315kVA              | SE           | Vegeta        | Standard             | Dyn11 |               315.0 |              20.0 |              0.4 |
| SE_Vegeta_Standard_400kVA              | SE           | Vegeta        | Standard             | Dyn11 |               400.0 |              20.0 |              0.4 |
| SE_Vegeta_Standard_500kVA              | SE           | Vegeta        | Standard             | Dyn11 |               500.0 |              20.0 |              0.4 |
| SE_Vegeta_Standard_630kVA              | SE           | Vegeta        | Standard             | Dyn11 |               630.0 |              20.0 |              0.4 |
| SE_Vegeta_Standard_800kVA              | SE           | Vegeta        | Standard             | Dyn11 |               800.0 |              20.0 |              0.4 |
| SE_Vegeta_Standard_1000kVA             | SE           | Vegeta        | Standard             | Dyn11 |              1000.0 |              20.0 |              0.4 |
| SE_Vegeta_Standard_1250kVA             | SE           | Vegeta        | Standard             | Dyn11 |              1250.0 |              20.0 |              0.4 |
| SE_Vegeta_Standard_1600kVA             | SE           | Vegeta        | Standard             | Dyn11 |              1600.0 |              20.0 |              0.4 |
| SE_Vegeta_Standard_2000kVA             | SE           | Vegeta        | Standard             | Dyn11 |              2000.0 |              20.0 |              0.4 |
| SE_Vegeta_Standard_2500kVA             | SE           | Vegeta        | Standard             | Dyn11 |              2500.0 |              20.0 |              0.4 |
| SE_Vegeta_Standard_3150kVA             | SE           | Vegeta        | Standard             | Dyn11 |              3150.0 |              20.0 |              0.4 |

The following data are available in this table:

- the **id**: a unique id among the catalogue.
- the **manufacturer**: two manufacturers are available. `"SE"` stands for "Schneider-Electric" and `"FT"` stands for
  "France Transfo".
- the product **range** which depends on the manufacturer
- the **efficiency** class of the transformer
- the **type** of the transformer.
- the nominal power, noted **sn**.
- the primary side phase to phase voltage, noted **uhv**.
- the secondary side phase to phase volage, noted **ulv**.

The `get_catalogue` method accepts arguments (in bold above) that can be used to filter the returned table. The
following command only retrieves transformer parameters of transformers with an efficiency of "A0Ak":

```pycon
>>> TransformerParameters.get_catalogue(efficiency="A0Ak")
```

| Id                     | Manufacturer | Product range | Efficiency | Type  | Nominal power (kVA) | High voltage (kV) | Low voltage (kV) |
| :--------------------- | :----------- | :------------ | :--------- | :---- | ------------------: | ----------------: | ---------------: |
| SE_Minera_A0Ak_50kVA   | SE           | Minera        | A0Ak       | Yzn11 |                50.0 |              20.0 |              0.4 |
| SE_Minera_A0Ak_100kVA  | SE           | Minera        | A0Ak       | Dyn11 |               100.0 |              20.0 |              0.4 |
| SE_Minera_A0Ak_160kVA  | SE           | Minera        | A0Ak       | Dyn11 |               160.0 |              20.0 |              0.4 |
| SE_Minera_A0Ak_250kVA  | SE           | Minera        | A0Ak       | Dyn11 |               250.0 |              20.0 |              0.4 |
| SE_Minera_A0Ak_315kVA  | SE           | Minera        | A0Ak       | Dyn11 |               315.0 |              20.0 |              0.4 |
| SE_Minera_A0Ak_400kVA  | SE           | Minera        | A0Ak       | Dyn11 |               400.0 |              20.0 |              0.4 |
| SE_Minera_A0Ak_500kVA  | SE           | Minera        | A0Ak       | Dyn11 |               500.0 |              20.0 |              0.4 |
| SE_Minera_A0Ak_630kVA  | SE           | Minera        | A0Ak       | Dyn11 |               630.0 |              20.0 |              0.4 |
| SE_Minera_A0Ak_800kVA  | SE           | Minera        | A0Ak       | Dyn11 |               800.0 |              20.0 |              0.4 |
| SE_Minera_A0Ak_1000kVA | SE           | Minera        | A0Ak       | Dyn11 |              1000.0 |              20.0 |              0.4 |
| SE_Minera_A0Ak_1250kVA | SE           | Minera        | A0Ak       | Dyn11 |              1250.0 |              20.0 |              0.4 |
| SE_Minera_A0Ak_1600kVA | SE           | Minera        | A0Ak       | Dyn11 |              1600.0 |              20.0 |              0.4 |
| SE_Minera_A0Ak_2000kVA | SE           | Minera        | A0Ak       | Dyn11 |              2000.0 |              20.0 |              0.4 |
| SE_Minera_A0Ak_2500kVA | SE           | Minera        | A0Ak       | Dyn11 |              2500.0 |              20.0 |              0.4 |

or only transformers with a wye winding on the primary side (using a regular expression)

```pycon
>>> TransformerParameters.get_catalogue(type=r"^y.*$")
```

| Id                       | Manufacturer | Product range | Efficiency | Type  | Nominal power (kVA) | High voltage (kV) | Low voltage (kV) |
| :----------------------- | :----------- | :------------ | :--------- | :---- | ------------------: | ----------------: | ---------------: |
| SE_Minera_A0Ak_50kVA     | SE           | Minera        | A0Ak       | Yzn11 |                50.0 |              20.0 |              0.4 |
| SE_Minera_B0Bk_50kVA     | SE           | Minera        | B0Bk       | Yzn11 |                50.0 |              20.0 |              0.4 |
| SE_Minera_C0Bk_50kVA     | SE           | Minera        | C0Bk       | Yzn11 |                50.0 |              20.0 |              0.4 |
| SE_Minera_Standard_50kVA | SE           | Minera        | Standard   | Yzn11 |                50.0 |              20.0 |              0.4 |

or only transformers meeting both criteria

```pycon
>>> TransformerParameters.get_catalogue(efficiency="A0Ak", type=r"^y.*$")
```

| Id                   | Manufacturer | Product range | Efficiency | Type  | Nominal power (kVA) | High voltage (kV) | Low voltage (kV) |
| :------------------- | :----------- | :------------ | :--------- | :---- | ------------------: | ----------------: | ---------------: |
| SE_Minera_A0Ak_50kVA | SE           | Minera        | A0Ak       | Yzn11 |                50.0 |              20.0 |              0.4 |

Among all the possible filters, the nominal power and voltages are expected in their default unit
(VA and V). You can also use the [Pint](https://pint.readthedocs.io/en/stable/) library to express
the values in different units. For instance, if you want to get transformer parameters with a
nominal power of 3150 kVA, the following two commands return the same table:

```pycon
>>> TransformerParameters.get_catalogue(sn=3150e3) # in VA by default

>>> from roseau.load_flow import Q_
... TransformerParameters.get_catalogue(sn=Q_(3150, "kVA"))
```

| Id                           | Manufacturer | Product range | Efficiency | Type  | Nominal power (kVA) | High voltage (kV) | Low voltage (kV) |
| :--------------------------- | :----------- | :------------ | :--------- | :---- | ------------------: | ----------------: | ---------------: |
| FT_Standard_Standard_3150kVA | FT           | Standard      | Standard   | Dyn11 |              3150.0 |              20.0 |              0.4 |
| SE_Vegeta_C0Bk_3150kVA       | SE           | Vegeta        | C0Bk       | Dyn11 |              3150.0 |              20.0 |              0.4 |
| SE_Vegeta_Standard_3150kVA   | SE           | Vegeta        | Standard   | Dyn11 |              3150.0 |              20.0 |              0.4 |

### Getting an instance

You can build a `TransformerParameters` instance from the catalogue using the class method `from_catalogue`.
You must filter the data to get a single transformer. You can apply the same filtering technique used for
the method `get_catalogue` to narrow down the result to a single transformer in the catalogue.

For instance, these parameters filter the catalogue down to a single transformer parameters:

```pycon
>>> TransformerParameters.from_catalogue(efficiency="A0Ak", type=r"^y.*$")
TransformerParameters(id='SE_Minera_A0Ak_50kVA')
```

The `id` filter can be directly used:

```pycon
>>> TransformerParameters.from_catalogue(id="SE_Minera_A0Ak_50kVA")
TransformerParameters(id='SE_Minera_A0Ak_50kVA')
```

In case no or several results match the parameters, an error is raised:

```pycon
>>> TransformerParameters.from_catalogue(manufacturer="ft")
RoseauLoadFlowException: Several transformers matching the query (manufacturer='ft') have been found:
'FT_Standard_Standard_100kVA', 'FT_Standard_Standard_160kVA', 'FT_Standard_Standard_250kVA',
'FT_Standard_Standard_315kVA', 'FT_Standard_Standard_400kVA', 'FT_Standard_Standard_500kVA',
'FT_Standard_Standard_630kVA', 'FT_Standard_Standard_800kVA', 'FT_Standard_Standard_1000kVA',
'FT_Standard_Standard_1250kVA', 'FT_Standard_Standard_1600kVA', 'FT_Standard_Standard_2000kVA',
'FT_Standard_Standard_2500kVA', 'FT_Standard_Standard_3150kVA'. [catalogue_several_found]
```

or if no results:

```pycon
>>> TransformerParameters.from_catalogue(manufacturer="unknown")
RoseauLoadFlowException: No manufacturer matching 'unknown' has been found. Available manufacturers
are 'FT', 'SE'. [catalogue_not_found]
```

(catalogues-lines)=

## Lines

_Roseau Load Flow_ is provided with a catalogue of line parameters. These parameters are available
through the class `LineParameters`.

### Source of data

The available lines data are based on the following sources:

- IEC standards including: IEC-60228, IEC-60287, IEC-60364
- Technique de l'ingénieur (French technical and scientific documentation)
- A model of cables used in the French public grid based on the work of Alain Coiffier

### Inspecting the catalogue

This catalogue can be retrieved in the form of a dataframe using:

```pycon
>>> from roseau.load_flow import LineParameters
>>> LineParameters.get_catalogue()
```

_Truncated to the first 50 lines_

| Name        | Resistance (ohm/km) | Reactance (ohm/km) | Susceptance (µS/km) | Maximal current (A) | Line type   | Conductor material | Cross-section (mm²) | Insulator type | Model    |
| :---------- | ------------------: | -----------------: | ------------------: | ------------------: | :---------- | :----------------- | ------------------: | :------------- | :------- |
| U_CU_75_PC  |                0.24 |                0.1 |         4.68097e-05 |             290.782 | UNDERGROUND | Cu                 |                  75 | PC             | coiffier |
| U_AL_147_PC |            0.204082 |                0.1 |         5.58575e-05 |               364.1 | UNDERGROUND | Al                 |                 147 | PC             | coiffier |
| U_CU_95_PP  |            0.189474 |                0.1 |          4.9323e-05 |             336.681 | UNDERGROUND | Cu                 |                  95 | PP             | coiffier |
| U_AL_116_PP |            0.258621 |                0.1 |         5.19619e-05 |             314.375 | UNDERGROUND | Al                 |                 116 | PP             | coiffier |
| U_CU_75_PU  |                0.24 |                0.1 |         0.000105715 |             290.782 | UNDERGROUND | Cu                 |                  75 | PU             | coiffier |
| U_CU_150_PU |                0.12 |                0.1 |         0.000141058 |             446.896 | UNDERGROUND | Cu                 |                 150 | PU             | coiffier |
| U_CU_150_PC |                0.12 |                0.1 |         5.62345e-05 |             446.896 | UNDERGROUND | Cu                 |                 150 | PC             | coiffier |
| U_AL_50_PP  |                 0.6 |                0.1 |         4.36681e-05 |             186.572 | UNDERGROUND | Al                 |                  50 | PP             | coiffier |
| U_AL_147_PP |            0.204082 |                0.1 |         5.58575e-05 |               364.1 | UNDERGROUND | Al                 |                 147 | PP             | coiffier |
| U_AL_50_SR  |                 0.6 |                0.1 |         4.86947e-05 |             186.572 | UNDERGROUND | Al                 |                  50 | SR             | coiffier |
| U_CU_95_PM  |            0.189474 |                0.1 |         0.000115139 |             336.681 | UNDERGROUND | Cu                 |                  95 | PM             | coiffier |
| U_CU_150    |               0.124 |          0.0960503 |         3.41234e-05 |                 420 | UNDERGROUND | Cu                 |                 150 |                | iec      |
| O_AL_55     |              0.5915 |           0.359804 |         3.18697e-06 |              195.25 | OVERHEAD    | Al                 |                  55 |                | iec      |
| O_AA_37     |             1.09695 |               0.35 |          1.5708e-06 |             133.221 | OVERHEAD    | AA                 |                  37 |                | coiffier |
| U_AL_2440   |           0.0122951 |                0.1 |          0.00122019 |              2078.1 | UNDERGROUND | Al                 |                2440 |                | coiffier |
| U_CU_38     |              0.4966 |           0.118845 |         2.65816e-05 |               198.6 | UNDERGROUND | Cu                 |                  38 |                | iec      |
| U_CU_35_SE  |            0.514286 |                0.1 |         4.63385e-05 |             181.281 | UNDERGROUND | Cu                 |                  35 | SE             | coiffier |
| U_CU_150_SE |                0.12 |                0.1 |         6.44026e-05 |             446.896 | UNDERGROUND | Cu                 |                 150 | SE             | coiffier |
| O_CU_33     |              0.5646 |           0.375852 |         3.04496e-06 |               183.4 | OVERHEAD    | Cu                 |                  33 |                | iec      |
| O_LA_37     |             1.28057 |               0.35 |          1.5708e-06 |             127.592 | OVERHEAD    | LA                 |                  37 |                | coiffier |
| O_AM_148    |            0.223649 |               0.35 |          1.5708e-06 |             363.418 | OVERHEAD    | AM                 |                 148 |                | coiffier |
| T_AL_95     |                0.32 |           0.102817 |         3.14727e-05 |                 227 | TWISTED     | Al                 |                  95 |                | iec      |
| O_CU_12     |             1.60333 |           0.407632 |         2.79805e-06 |                  90 | OVERHEAD    | Cu                 |                  12 |                | iec      |
| O_AA_80     |            0.507337 |               0.35 |          1.5708e-06 |             183.105 | OVERHEAD    | AA                 |                  80 |                | coiffier |
| T_AL_50     |               0.641 |           0.113705 |         2.79758e-05 |                 146 | TWISTED     | Al                 |                  50 |                | iec      |
| O_CU_29     |              0.6458 |           0.379911 |         3.01102e-06 |               170.2 | OVERHEAD    | Cu                 |                  29 |                | iec      |
| O_CU_22     |               0.868 |            0.38859 |         2.94094e-06 |             144.667 | OVERHEAD    | Cu                 |                  22 |                | iec      |
| O_AM_43     |            0.769767 |               0.35 |          1.5708e-06 |             168.886 | OVERHEAD    | AM                 |                  43 |                | coiffier |
| O_AM_117    |            0.282906 |               0.35 |          1.5708e-06 |             314.137 | OVERHEAD    | AM                 |                 117 |                | coiffier |
| O_AM_34     |            0.973529 |               0.35 |          1.5708e-06 |             146.003 | OVERHEAD    | AM                 |                  34 |                | coiffier |
| O_LA_147    |             0.32232 |               0.35 |          1.5708e-06 |              344.24 | OVERHEAD    | LA                 |                 147 |                | coiffier |
| O_AA_116    |            0.349888 |               0.35 |          1.5708e-06 |             299.133 | OVERHEAD    | AA                 |                 116 |                | coiffier |
| O_AA_147    |            0.276102 |               0.35 |          1.5708e-06 |             346.447 | OVERHEAD    | AA                 |                 147 |                | coiffier |
| O_AA_22     |             1.84486 |               0.35 |          1.5708e-06 |              96.514 | OVERHEAD    | AA                 |                  22 |                | coiffier |
| O_CU_38     |              0.4966 |            0.37142 |          3.0829e-06 |               198.6 | OVERHEAD    | Cu                 |                  38 |                | iec      |
| T_AL_150    |               0.206 |          0.0960503 |         3.41234e-05 |                 304 | TWISTED     | Al                 |                 150 |                | iec      |
| U_AL_70     |               0.443 |           0.107797 |         2.97707e-05 |                 214 | UNDERGROUND | Al                 |                  70 |                | iec      |
| O_AM_22     |             1.50455 |               0.35 |          1.5708e-06 |             111.467 | OVERHEAD    | AM                 |                  22 |                | coiffier |
| U_CU_16     |                1.15 |           0.136834 |         2.26339e-05 |                 126 | UNDERGROUND | Cu                 |                  16 |                | iec      |
| O_LA_228    |            0.207811 |               0.35 |          1.5708e-06 |             451.902 | OVERHEAD    | LA                 |                 228 |                | coiffier |
| U_AL_29     |              1.0672 |           0.124182 |         2.52738e-05 |               134.6 | UNDERGROUND | Al                 |                  29 |                | iec      |
| O_AM_55     |            0.601818 |               0.35 |          1.5708e-06 |             196.729 | OVERHEAD    | AM                 |                  55 |                | coiffier |
| O_LA_60     |            0.789683 |               0.35 |          1.5708e-06 |             153.193 | OVERHEAD    | LA                 |                  60 |                | coiffier |
| O_AA_38     |             1.06808 |               0.35 |          1.5708e-06 |             135.442 | OVERHEAD    | AA                 |                  38 |                | coiffier |
| O_AA_55     |            0.737945 |               0.35 |          1.5708e-06 |             145.148 | OVERHEAD    | AA                 |                  55 |                | coiffier |
| O_LA_38     |             1.24687 |               0.35 |          1.5708e-06 |             129.719 | OVERHEAD    | LA                 |                  38 |                | coiffier |
| O_CU_14     |             1.37667 |           0.402789 |         2.83305e-06 |                 105 | OVERHEAD    | Cu                 |                  14 |                | iec      |
| O_AA_60     |             0.67645 |               0.35 |          1.5708e-06 |             153.193 | OVERHEAD    | AA                 |                  60 |                | coiffier |
| O_AM_76     |            0.435526 |               0.35 |          1.5708e-06 |             240.408 | OVERHEAD    | AM                 |                  76 |                | coiffier |
| O_CU_7      |              2.7675 |           0.424565 |         2.68217e-06 |               59.25 | OVERHEAD    | Cu                 |                   7 |                | iec      |

The following data are available in this table:

- the **name**. A name that contains the type of the line, the material of the conductor, the
  cross-section area, and optionally the insulator type. It is in the form
  `{line_type}_{conductor_material}_{cross_section}_{insulator_type}`.
- the **line type**. It can be `"OVERHEAD"`, `"UNDERGROUND"` or `"TWISTED"`.
- the **conductor material**. See the {class}`~roseau.load_flow.ConductorType` class.
- the **insulator type**. See the {class}`~roseau.load_flow.InsulatorType` class.
- the **cross-section** of the conductor in mm².
- the **model** of the line parameters. It can be either `"iec"` or `"coiffier"`.

in addition to the following physical parameters:

- the _resistance_ of the line in ohm/km.
- the _reactance_ of the line in ohm/km.
- the _susceptance_ of the line in µS/km.
- the _maximal current_ of the line in A.

The `get_catalogue` method accepts arguments (in bold above) that can be used to filter the returned
table. The following command only returns line parameters made of Aluminum using the IEC model:

```pycon
>>> LineParameters.get_catalogue(conductor_type="al", model="iec")
```

_Truncated to the first 10 lines_

| Name     | Resistance (ohm/km) | Reactance (ohm/km) | Susceptance (µS/km) | Maximal current (A) | Line type   | Conductor material | Cross-section (mm²) | Insulator type | Model |
| :------- | ------------------: | -----------------: | ------------------: | ------------------: | :---------- | :----------------- | ------------------: | :------------- | :---- |
| O_AL_55  |              0.5915 |           0.359804 |         3.18697e-06 |              195.25 | OVERHEAD    | Al                 |                  55 |                | iec   |
| T_AL_95  |                0.32 |           0.102817 |         3.14727e-05 |                 227 | TWISTED     | Al                 |                  95 |                | iec   |
| T_AL_50  |               0.641 |           0.113705 |         2.79758e-05 |                 146 | TWISTED     | Al                 |                  50 |                | iec   |
| T_AL_150 |               0.206 |          0.0960503 |         3.41234e-05 |                 304 | TWISTED     | Al                 |                 150 |                | iec   |
| U_AL_70  |               0.443 |           0.107797 |         2.97707e-05 |                 214 | UNDERGROUND | Al                 |                  70 |                | iec   |
| U_AL_29  |              1.0672 |           0.124182 |         2.52738e-05 |               134.6 | UNDERGROUND | Al                 |                  29 |                | iec   |
| U_AL_150 |               0.206 |          0.0960503 |         3.41234e-05 |                 325 | UNDERGROUND | Al                 |                 150 |                | iec   |
| U_AL_240 |               0.125 |          0.0899296 |         3.69374e-05 |                 428 | UNDERGROUND | Al                 |                 240 |                | iec   |
| U_AL_50  |               0.641 |           0.113705 |         2.79758e-05 |                 175 | UNDERGROUND | Al                 |                  50 |                | iec   |
| U_AL_95  |                0.32 |           0.102817 |         3.14727e-05 |                 252 | UNDERGROUND | Al                 |                  95 |                | iec   |

or only lines with a cross section of 240 mm² (using a regular expression)

```pycon
>>> LineParameters.get_catalogue(section=240)
```

_Truncated to the first 10 lines_

| Name        | Resistance (ohm/km) | Reactance (ohm/km) | Susceptance (µS/km) | Maximal current (A) | Line type   | Conductor material | Cross-section (mm²) | Insulator type | Model    |
| :---------- | ------------------: | -----------------: | ------------------: | ------------------: | :---------- | :----------------- | ------------------: | :------------- | :------- |
| U_AL_240    |               0.125 |          0.0899296 |         3.69374e-05 |                 428 | UNDERGROUND | Al                 |                 240 |                | iec      |
| U_CU_240    |              0.0775 |          0.0899296 |         3.69374e-05 |                 549 | UNDERGROUND | Cu                 |                 240 |                | iec      |
| U_AL_240_S3 |               0.125 |                0.1 |         7.85398e-05 |             493.418 | UNDERGROUND | Al                 |                 240 | S3             | coiffier |
| U_AL_240_SC |               0.125 |                0.1 |         9.80177e-05 |             493.418 | UNDERGROUND | Al                 |                 240 | SC             | coiffier |
| U_AL_240_S6 |               0.125 |                0.1 |         7.85398e-05 |             493.418 | UNDERGROUND | Al                 |                 240 | S6             | coiffier |
| U_AL_240_SO |               0.125 |                0.1 |         0.000115611 |             493.418 | UNDERGROUND | Al                 |                 240 | SO             | coiffier |
| T_AL_240    |               0.125 |          0.0899296 |         3.69374e-05 |                 409 | TWISTED     | Al                 |                 240 |                | iec      |
| U_CU_240_SO |               0.075 |                0.1 |         0.000115611 |             598.082 | UNDERGROUND | Cu                 |                 240 | SO             | coiffier |
| U_CU_240_S6 |               0.075 |                0.1 |         7.85398e-05 |             598.082 | UNDERGROUND | Cu                 |                 240 | S6             | coiffier |
| U_AL_240_PU |               0.125 |                0.1 |         0.000183469 |             493.418 | UNDERGROUND | Al                 |                 240 | PU             | coiffier |

or only lines meeting both criteria

```pycon
>>> LineParameters.get_catalogue(conductor_type="al", model="iec", section=240)
```

| Name     | Resistance (ohm/km) | Reactance (ohm/km) | Susceptance (µS/km) | Maximal current (A) | Line type   | Conductor material | Cross-section (mm²) | Insulator type | Model |
| :------- | ------------------: | -----------------: | ------------------: | ------------------: | :---------- | :----------------- | ------------------: | :------------- | :---- |
| U_AL_240 |               0.125 |          0.0899296 |         3.69374e-05 |                 428 | UNDERGROUND | Al                 |                 240 |                | iec   |
| T_AL_240 |               0.125 |          0.0899296 |         3.69374e-05 |                 409 | TWISTED     | Al                 |                 240 |                | iec   |
| O_AL_240 |               0.125 |           0.313518 |         3.68228e-06 |                 490 | OVERHEAD    | Al                 |                 240 |                | iec   |

When filtering by the cross-section area, it is expected to provide a numeric value in mm² or to use a pint quantity.

### Getting an instance

You can build a `LineParameters` instance from the catalogue using the class method `from_catalogue`.
You must filter the data to get a single line. You can apply the same filtering technique used for
the method `get_catalogue` to narrow down the result to a single line in the catalogue.

For instance, these parameters filter the results down to a single line parameters:

```pycon
>>> LineParameters.from_catalogue(line_type="underground", conductor_type="al", model="iec", section=240)
LineParameters(id='U_AL_240')
```

Or you can use the `id` filter directly:

```pycon
>>> LineParameters.from_catalogue(id="U_AL_240", model="iec")
LineParameters(id='U_AL_240')
```

In case no or several results match the parameters, an error is raised:

```pycon
>>> LineParameters.from_catalogue(id= r"^U_AL", model="iec")
RoseauLoadFlowException: Several line parameters matching the query (id='^U_AL', model='iec') have been found:
'U_AL_70', 'U_AL_29', 'U_AL_150', 'U_AL_240', 'U_AL_50', 'U_AL_95', 'U_AL_75', 'U_AL_147', 'U_AL_116',
'U_AL_40', 'U_AL_38', 'U_AL_22', 'U_AL_37', 'U_AL_630', 'U_AL_120', 'U_AL_35', 'U_AL_60', 'U_AL_34',
'U_AL_25', 'U_AL_16', 'U_AL_600', 'U_AL_239', 'U_AL_149', 'U_AL_80', 'U_AL_500'. [catalogue_several_found]
```

or if no results:

```pycon
>>> LineParameters.from_catalogue(id="unknown")
RoseauLoadFlowException: No id matching 'unknown' has been found. Available ids are 'U_CU_75_PC',
'U_AL_147_PC', 'U_CU_95_PP', 'U_AL_116_PP', 'U_CU_75_PU', 'U_CU_150_PU', 'U_CU_150_PC', 'U_AL_50_PP',
'U_AL_147_PP', 'U_AL_50_SR', 'U_CU_95_PM', 'U_CU_150', 'O_AL_55', 'O_AA_37', 'U_AL_2440', 'U_CU_38',
'U_CU_35_SE', 'U_CU_150_SE', 'O_CU_33', 'O_LA_37', 'O_AM_148', 'T_AL_95', 'O_CU_12', 'O_AA_80',
'T_AL_50', 'O_CU_29', 'O_CU_22', 'O_AM_43', 'O_AM_117', 'O_AM_34', 'O_LA_147', 'O_AA_116', 'O_AA_147',
'O_AA_22', 'O_CU_38', 'T_AL_150', 'U_AL_70', 'O_AM_22', 'U_CU_16', 'O_LA_228', [...]. [catalogue_not_found]
```
