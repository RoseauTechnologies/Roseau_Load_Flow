---
myst:
  html_meta:
    "description lang=en": |
      Roseau Load Flow comes with a catalogue of components including numerous models of medium and low voltage
      networks, transformers and lines.
    "description lang=fr": |
      Roseau Load Flow est livré avec un catalogue de composants comportant de nombreux modèles de réseaux
      moyenne-tension et basse tension, de transformateurs et de lignes.
    "keywords lang=fr": |
      simulation, réseau, électrique, réseaux, MT, BT, moyenne tension, basse tension, transformateurs, lignes, modèle
    "keywords lang=en": simulation, distribution grid, MT, LV, transformer, cables, model
---

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

All these networks are built from open data available in France. **The complete model of the French distribution
network can be provided on demand**. Please email us at
[contact@roseautechnologies.com](mailto:contact@roseautechnologies.com).

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

- For Schneider-Electric EcoDesign products (_AA0Ak_ efficiency class):
  [Minera](../_static/Transformer/Minera-EcoDesign2021-20kV_ZZ6921.pdf),
  [Vegeta](../_static/Transformer/Vegeta-EcoDesign2021-20kV_ZZ6924.pdf),
  [Trihal](../_static/Transformer/Trihal-EcoDesign2021-20kV_ZZ6925.pdf)
- For other Schneider-Electric products: See [this document](../_static/Transformer/2023_03_31_Fiche_Technique_Schneider_Electric.pdf)
  on pages 19, 21 and 22.
- For France Transfo: See [this document](../_static/Transformer/2023_03_30_Fiche_Technique_France_Transfo.pdf).

Pull requests to add some other sources are welcome!

### Inspecting the catalogue

This catalogue can be retrieved in the form of a dataframe using:

```pycon
>>> from roseau.load_flow import TransformerParameters
>>> TransformerParameters.get_catalogue()
```

_Truncated output_

| Id                           | Manufacturer | Product range | Efficiency | Nominal power (kVA) | Type  | High voltage (kV) | Low voltage (kV) |
| :--------------------------- | :----------- | :------------ | :--------- | ------------------: | :---- | ----------------: | ---------------: |
| FT_Standard_Standard_100kVA  | FT           | Standard      | Standard   |                 100 | Dyn11 |                20 |              0.4 |
| FT_Standard_Standard_160kVA  | FT           | Standard      | Standard   |                 160 | Dyn11 |                20 |              0.4 |
| FT_Standard_Standard_250kVA  | FT           | Standard      | Standard   |                 250 | Dyn11 |                20 |              0.4 |
| FT_Standard_Standard_315kVA  | FT           | Standard      | Standard   |                 315 | Dyn11 |                20 |              0.4 |
| FT_Standard_Standard_400kVA  | FT           | Standard      | Standard   |                 400 | Dyn11 |                20 |              0.4 |
| FT_Standard_Standard_500kVA  | FT           | Standard      | Standard   |                 500 | Dyn11 |                20 |              0.4 |
| FT_Standard_Standard_630kVA  | FT           | Standard      | Standard   |                 630 | Dyn11 |                20 |              0.4 |
| FT_Standard_Standard_800kVA  | FT           | Standard      | Standard   |                 800 | Dyn11 |                20 |              0.4 |
| FT_Standard_Standard_1000kVA | FT           | Standard      | Standard   |                1000 | Dyn11 |                20 |              0.4 |
| FT_Standard_Standard_1250kVA | FT           | Standard      | Standard   |                1250 | Dyn11 |                20 |              0.4 |
| FT_Standard_Standard_1600kVA | FT           | Standard      | Standard   |                1600 | Dyn11 |                20 |              0.4 |
| FT_Standard_Standard_2000kVA | FT           | Standard      | Standard   |                2000 | Dyn11 |                20 |              0.4 |
| FT_Standard_Standard_2500kVA | FT           | Standard      | Standard   |                2500 | Dyn11 |                20 |              0.4 |
| FT_Standard_Standard_3150kVA | FT           | Standard      | Standard   |                3150 | Dyn11 |                20 |              0.4 |
| SE_Minera_AA0Ak_160kVA       | SE           | Minera        | AA0Ak      |                 160 | Dyn11 |                20 |              0.4 |
| SE_Minera_AA0Ak_250kVA       | SE           | Minera        | AA0Ak      |                 250 | Dyn11 |                20 |              0.4 |
| SE_Minera_AA0Ak_400kVA       | SE           | Minera        | AA0Ak      |                 400 | Dyn11 |                20 |              0.4 |
| SE_Minera_AA0Ak_630kVA       | SE           | Minera        | AA0Ak      |                 630 | Dyn11 |                20 |              0.4 |
| SE_Minera_AA0Ak_800kVA       | SE           | Minera        | AA0Ak      |                 800 | Dyn11 |                20 |              0.4 |
| SE_Minera_AA0Ak_1000kVA      | SE           | Minera        | AA0Ak      |                1000 | Dyn11 |                20 |              0.4 |
| SE_Minera_AA0Ak_1250kVA      | SE           | Minera        | AA0Ak      |                1250 | Dyn11 |                20 |              0.4 |
| SE_Minera_AA0Ak_1600kVA      | SE           | Minera        | AA0Ak      |                1600 | Dyn11 |                20 |              0.4 |
| SE_Minera_AA0Ak_2000kVA      | SE           | Minera        | AA0Ak      |                2000 | Dyn11 |                20 |              0.4 |
| SE_Minera_AA0Ak_2500kVA      | SE           | Minera        | AA0Ak      |                2500 | Dyn11 |                20 |              0.4 |
| SE_Minera_AA0Ak_3150kVA      | SE           | Minera        | AA0Ak      |                3150 | Dyn11 |                20 |              0.4 |
| SE_Minera_A0Ak_50kVA         | SE           | Minera        | A0Ak       |                  50 | Yzn11 |                20 |              0.4 |
| SE_Minera_A0Ak_100kVA        | SE           | Minera        | A0Ak       |                 100 | Dyn11 |                20 |              0.4 |
| SE_Minera_A0Ak_160kVA        | SE           | Minera        | A0Ak       |                 160 | Dyn11 |                20 |              0.4 |
| SE_Minera_A0Ak_250kVA        | SE           | Minera        | A0Ak       |                 250 | Dyn11 |                20 |              0.4 |
| SE_Minera_A0Ak_315kVA        | SE           | Minera        | A0Ak       |                 315 | Dyn11 |                20 |              0.4 |
| SE_Minera_A0Ak_400kVA        | SE           | Minera        | A0Ak       |                 400 | Dyn11 |                20 |              0.4 |
| SE_Minera_A0Ak_500kVA        | SE           | Minera        | A0Ak       |                 500 | Dyn11 |                20 |              0.4 |
| SE_Minera_A0Ak_630kVA        | SE           | Minera        | A0Ak       |                 630 | Dyn11 |                20 |              0.4 |
| SE_Minera_A0Ak_800kVA        | SE           | Minera        | A0Ak       |                 800 | Dyn11 |                20 |              0.4 |
| SE_Minera_A0Ak_1000kVA       | SE           | Minera        | A0Ak       |                1000 | Dyn11 |                20 |              0.4 |
| SE_Minera_A0Ak_1250kVA       | SE           | Minera        | A0Ak       |                1250 | Dyn11 |                20 |              0.4 |
| SE_Minera_A0Ak_1600kVA       | SE           | Minera        | A0Ak       |                1600 | Dyn11 |                20 |              0.4 |
| SE_Minera_A0Ak_2000kVA       | SE           | Minera        | A0Ak       |                2000 | Dyn11 |                20 |              0.4 |
| SE_Minera_A0Ak_2500kVA       | SE           | Minera        | A0Ak       |                2500 | Dyn11 |                20 |              0.4 |
| SE_Minera_B0Bk_50kVA         | SE           | Minera        | B0Bk       |                  50 | Yzn11 |                20 |              0.4 |
| SE_Minera_B0Bk_100kVA        | SE           | Minera        | B0Bk       |                 100 | Dyn11 |                20 |              0.4 |
| SE_Minera_B0Bk_160kVA        | SE           | Minera        | B0Bk       |                 160 | Dyn11 |                20 |              0.4 |
| SE_Minera_B0Bk_250kVA        | SE           | Minera        | B0Bk       |                 250 | Dyn11 |                20 |              0.4 |
| SE_Minera_B0Bk_315kVA        | SE           | Minera        | B0Bk       |                 315 | Dyn11 |                20 |              0.4 |
| SE_Minera_B0Bk_400kVA        | SE           | Minera        | B0Bk       |                 400 | Dyn11 |                20 |              0.4 |
| SE_Minera_B0Bk_500kVA        | SE           | Minera        | B0Bk       |                 500 | Dyn11 |                20 |              0.4 |
| SE_Minera_B0Bk_630kVA        | SE           | Minera        | B0Bk       |                 630 | Dyn11 |                20 |              0.4 |
| SE_Minera_B0Bk_800kVA        | SE           | Minera        | B0Bk       |                 800 | Dyn11 |                20 |              0.4 |
| SE_Minera_B0Bk_1000kVA       | SE           | Minera        | B0Bk       |                1000 | Dyn11 |                20 |              0.4 |
| SE_Minera_B0Bk_1250kVA       | SE           | Minera        | B0Bk       |                1250 | Dyn11 |                20 |              0.4 |

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

### Inspecting the catalogue

This catalogue can be retrieved in the form of a dataframe using:

```pycon
>>> from roseau.load_flow import LineParameters
>>> LineParameters.get_catalogue()
```

_Truncated output_

| Name     | Line type   | Conductor material | Insulator type | Cross-section (mm²) | Resistance (ohm/km) | Reactance (ohm/km) | Susceptance (µS/km) | Maximal current (A) |
| :------- | :---------- | :----------------- | :------------- | ------------------: | ------------------: | -----------------: | ------------------: | ------------------: |
| T_AM_80  | twisted     | am                 |                |                  80 |            0.457596 |           0.105575 |          3.0507e-05 |                 203 |
| U_CU_19  | underground | cu                 |                |                  19 |               1.009 |           0.133054 |         2.33629e-05 |                 138 |
| O_AM_33  | overhead    | am                 |                |                  33 |             1.08577 |           0.375852 |           3.045e-06 |                 142 |
| U_CU_150 | underground | cu                 |                |                 150 |               0.124 |          0.0960503 |         3.41234e-05 |                 420 |
| O_AM_74  | overhead    | am                 |                |                  74 |            0.491898 |           0.350482 |          3.2757e-06 |                 232 |
| T_AM_34  | twisted     | am                 |                |                  34 |             1.04719 |           0.121009 |         2.60354e-05 |                 118 |
| T_AM_50  | twisted     | am                 |                |                  50 |            0.744842 |           0.113705 |         2.79758e-05 |                 146 |
| O_AM_95  | overhead    | am                 |                |                  95 |             0.37184 |           0.342634 |          3.3543e-06 |                 266 |
| U_CU_100 | underground | cu                 |                |                 100 |               0.185 |           0.102016 |         3.17647e-05 |                 339 |
| T_CU_38  | twisted     | cu                 |                |                  38 |              0.4966 |           0.118845 |         2.65816e-05 |                 165 |
| O_AM_100 | overhead    | am                 |                |                 100 |            0.356269 |           0.341022 |           3.371e-06 |                 276 |
| U_AM_60  | underground | am                 |                |                  60 |            0.629804 |            0.11045 |         2.89372e-05 |                 194 |
| T_AM_79  | twisted     | am                 |                |                  79 |            0.463313 |           0.105781 |         3.04371e-05 |                 201 |
| T_CU_60  | twisted     | cu                 |                |                  60 |              0.3275 |            0.11045 |         2.89372e-05 |                 219 |
| U_AM_240 | underground | am                 |                |                 240 |             0.14525 |          0.0899296 |         3.69374e-05 |                 428 |
| O_AL_37  | overhead    | al                 |                |                  37 |            0.837733 |           0.372257 |          3.0757e-06 |                 152 |
| U_AM_93  | underground | am                 |                |                  93 |            0.383274 |           0.103152 |         3.13521e-05 |                 249 |
| O_AM_28  | overhead    | am                 |                |                  28 |             1.27866 |           0.381013 |          3.0019e-06 |                 130 |
| T_AL_90  | twisted     | al                 |                |                  90 |              0.3446 |           0.103672 |         3.11668e-05 |                 219 |
| O_AM_79  | overhead    | am                 |                |                  79 |            0.463313 |           0.348428 |          3.2959e-06 |                 240 |

The following data are available in this table:

- the **name**. A name that contains the type of the line, the material of the conductor, the
  cross-section area, and optionally the insulator type. It is in the form
  `{line_type}_{conductor_material}_{cross_section}_{insulator_type}`.
- the **line type**. It can be `"OVERHEAD"`, `"UNDERGROUND"` or `"TWISTED"`.
- the **conductor material**. See the {class}`~roseau.load_flow.ConductorType` class.
- the **insulator type**. See the {class}`~roseau.load_flow.InsulatorType` class.
- the **cross-section** of the conductor in mm².

in addition to the following calculated physical parameters:

- the _resistance_ of the line in ohm/km.
- the _reactance_ of the line in ohm/km.
- the _susceptance_ of the line in µS/km.
- the _maximal current_ of the line in A.

The `get_catalogue` method accepts arguments (in bold above) that can be used to filter the returned
table. The following command only returns line parameters made of Aluminum:

```pycon
>>> LineParameters.get_catalogue(conductor_type="al")
```

_Truncated output_

| Name     | Line type   | Conductor material | Insulator type | Cross-section (mm²) | Resistance (ohm/km) | Reactance (ohm/km) | Susceptance (µS/km) | Maximal current (A) |
| :------- | :---------- | :----------------- | :------------- | ------------------: | ------------------: | -----------------: | ------------------: | ------------------: |
| U_AL_117 | underground | al                 |                |                 117 |             0.26104 |          0.0996298 |          3.2668e-05 |                 286 |
| U_AL_33  | underground | al                 |                |                  33 |              0.9344 |           0.121598 |         2.58907e-05 |                 144 |
| U_AL_69  | underground | al                 |                |                  69 |              0.4529 |           0.108041 |         2.96921e-05 |                 212 |
| T_AL_228 | twisted     | al                 |                |                 228 |            0.133509 |          0.0905569 |         3.66279e-05 |                 395 |
| U_AL_150 | underground | al                 |                |                 150 |               0.206 |          0.0960503 |         3.41234e-05 |                 325 |
| T_AL_69  | twisted     | al                 |                |                  69 |              0.4529 |           0.108041 |         2.96921e-05 |                 185 |
| O_AL_116 | overhead    | al                 |                |                 116 |             0.26372 |           0.336359 |            3.42e-06 |                 310 |
| U_AL_50  | underground | al                 |                |                  50 |               0.641 |           0.113705 |         2.79758e-05 |                 175 |
| U_AL_93  | underground | al                 |                |                  93 |             0.32984 |           0.103152 |         3.13521e-05 |                 249 |
| T_AL_59  | twisted     | al                 |                |                  59 |              0.5519 |           0.110744 |         2.88474e-05 |                 164 |

or only lines with a cross-section of 240 mm² (using a regular expression)

```pycon
>>> LineParameters.get_catalogue(section=240)
```

| Name     | Line type   | Conductor material | Insulator type | Cross-section (mm²) | Resistance (ohm/km) | Reactance (ohm/km) | Susceptance (µS/km) | Maximal current (A) |
| :------- | :---------- | :----------------- | :------------- | ------------------: | ------------------: | -----------------: | ------------------: | ------------------: |
| O_AL_240 | overhead    | al                 |                |                 240 |               0.125 |           0.313518 |          3.6823e-06 |                 490 |
| O_CU_240 | overhead    | cu                 |                |                 240 |              0.0775 |           0.313518 |          3.6823e-06 |                 630 |
| O_AM_240 | overhead    | am                 |                |                 240 |             0.14525 |           0.313518 |          3.6823e-06 |                 490 |
| U_AL_240 | underground | al                 |                |                 240 |               0.125 |          0.0899296 |         3.69374e-05 |                 428 |
| U_CU_240 | underground | cu                 |                |                 240 |              0.0775 |          0.0899296 |         3.69374e-05 |                 549 |
| U_AM_240 | underground | am                 |                |                 240 |             0.14525 |          0.0899296 |         3.69374e-05 |                 428 |
| T_AL_240 | twisted     | al                 |                |                 240 |               0.125 |          0.0899296 |         3.69374e-05 |                 409 |
| T_CU_240 | twisted     | cu                 |                |                 240 |              0.0775 |          0.0899296 |         3.69374e-05 |                 538 |
| T_AM_240 | twisted     | am                 |                |                 240 |             0.14525 |          0.0899296 |         3.69374e-05 |                 409 |

or only lines meeting both criteria

```pycon
>>> LineParameters.get_catalogue(conductor_type="al", section=240)
```

| Name     | Line type   | Conductor material | Insulator type | Cross-section (mm²) | Resistance (ohm/km) | Reactance (ohm/km) | Susceptance (µS/km) | Maximal current (A) |
| :------- | :---------- | :----------------- | :------------- | ------------------: | ------------------: | -----------------: | ------------------: | ------------------: |
| O_AL_240 | overhead    | al                 |                |                 240 |               0.125 |           0.313518 |          3.6823e-06 |                 490 |
| U_AL_240 | underground | al                 |                |                 240 |               0.125 |          0.0899296 |         3.69374e-05 |                 428 |
| T_AL_240 | twisted     | al                 |                |                 240 |               0.125 |          0.0899296 |         3.69374e-05 |                 409 |

When filtering by the cross-section area, it is expected to provide a numeric value in mm² or to use a pint quantity.

### Getting an instance

You can build a `LineParameters` instance from the catalogue using the class method `from_catalogue`.
You must filter the data to get a single line. You can apply the same filtering technique used for
the method `get_catalogue` to narrow down the result to a single line in the catalogue.

For instance, these parameters filter the results down to a single line parameters:

```pycon
>>> LineParameters.from_catalogue(line_type="underground", conductor_type="al", section=240)
LineParameters(id='U_AL_240')
```

Or you can use the `name` filter directly:

```pycon
>>> LineParameters.from_catalogue(name="U_AL_240")
LineParameters(id='U_AL_240')
```

As you can see, the `id` of the created instance is the same as the name in the catalogue. You can
override this behaviour by passing the `id` parameter to `from_catalogue`.

In case no or several results match the parameters, an error is raised:

```pycon
>>> LineParameters.from_catalogue(name= r"^U_AL")
RoseauLoadFlowException: Several line parameters matching the query (name='^U_AL_') have been found:
'U_AL_19', 'U_AL_20', 'U_AL_22', 'U_AL_25', 'U_AL_28', 'U_AL_29', 'U_AL_33', 'U_AL_34', 'U_AL_37',
'U_AL_38', 'U_AL_40', 'U_AL_43', 'U_AL_48', 'U_AL_50', 'U_AL_54', 'U_AL_55', 'U_AL_59', 'U_AL_60',
'U_AL_69', 'U_AL_70', 'U_AL_74', 'U_AL_75', 'U_AL_79', 'U_AL_80', 'U_AL_90', 'U_AL_93', 'U_AL_95',
'U_AL_100', 'U_AL_116', 'U_AL_117', 'U_AL_120', 'U_AL_147', 'U_AL_148', 'U_AL_150', 'U_AL_228',
'U_AL_240', 'U_AL_288'. [catalogue_several_found]
```

or if no results:

```pycon
>>> LineParameters.from_catalogue(name="unknown")
RoseauLoadFlowException: No name matching 'unknown' has been found. Available names are 'O_AL_12',
'O_AL_13', 'O_AL_14', 'O_AL_19', 'O_AL_20', 'O_AL_22', 'O_AL_25', 'O_AL_28', 'O_AL_29', 'O_AL_33',
'O_AL_34', 'O_AL_37', 'O_AL_38', 'O_AL_40', 'O_AL_43', 'O_AL_48', 'O_AL_50', 'O_AL_54', 'O_AL_55',
'O_AL_59', 'O_AL_60', 'O_AL_69', 'O_AL_70', 'O_AL_74', 'O_AL_75', 'O_AL_79', 'O_AL_80', 'O_AL_90',
'O_AL_93', 'O_AL_95', 'O_AL_100', 'O_AL_116', 'O_AL_117', 'O_AL_120', 'O_AL_147', 'O_AL_148', 'O_AL_150',
'O_AL_228', 'O_AL_240', 'O_AL_288', 'O_CU_3', 'O_CU_7', 'O_CU_12', 'O_CU_13', [...]. [catalogue_not_found]
```
