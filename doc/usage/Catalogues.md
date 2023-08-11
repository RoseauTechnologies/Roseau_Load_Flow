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

### Printing the catalogue

This catalogue can be printed to the terminal:

```pycon
>>> from roseau.load_flow import ElectricalNetwork
>>> ElectricalNetwork.print_catalogue()
```

| Name                                                                              | Nb buses | Nb branches | Nb loads | Nb sources | Nb grounds | Nb potential refs | Available load points |
| :-------------------------------------------------------------------------------- | -------: | ----------: | -------: | ---------: | ---------: | ----------------: | --------------------: |
| <a href="../_static/Network/LVFeeder00939.html" target="_blank">LVFeeder00939</a> |        8 |           7 |       12 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/LVFeeder02639.html" target="_blank">LVFeeder02639</a> |        7 |           6 |       10 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/LVFeeder04790.html" target="_blank">LVFeeder04790</a> |        4 |           3 |        4 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/LVFeeder06713.html" target="_blank">LVFeeder06713</a> |        3 |           2 |        2 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/LVFeeder06926.html" target="_blank">LVFeeder06926</a> |        3 |           2 |        2 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/LVFeeder06975.html" target="_blank">LVFeeder06975</a> |        6 |           5 |        8 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/LVFeeder18498.html" target="_blank">LVFeeder18498</a> |       18 |          17 |       32 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/LVFeeder18769.html" target="_blank">LVFeeder18769</a> |        7 |           6 |       10 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/LVFeeder19558.html" target="_blank">LVFeeder19558</a> |        3 |           2 |        2 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/LVFeeder20256.html" target="_blank">LVFeeder20256</a> |        9 |           8 |       14 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/LVFeeder23832.html" target="_blank">LVFeeder23832</a> |        3 |           2 |        2 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/LVFeeder24400.html" target="_blank">LVFeeder24400</a> |        4 |           3 |        4 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/LVFeeder27429.html" target="_blank">LVFeeder27429</a> |       11 |          10 |       18 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/LVFeeder27681.html" target="_blank">LVFeeder27681</a> |        3 |           2 |        2 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/LVFeeder30216.html" target="_blank">LVFeeder30216</a> |        9 |           8 |       14 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/LVFeeder31441.html" target="_blank">LVFeeder31441</a> |        4 |           3 |        4 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/LVFeeder36284.html" target="_blank">LVFeeder36284</a> |        5 |           4 |        6 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/LVFeeder36360.html" target="_blank">LVFeeder36360</a> |        9 |           8 |       14 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/LVFeeder37263.html" target="_blank">LVFeeder37263</a> |        3 |           2 |        2 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/LVFeeder38211.html" target="_blank">LVFeeder38211</a> |        6 |           5 |        8 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/MVFeeder004.html" target="_blank">MVFeeder004</a>     |       17 |          16 |       10 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/MVFeeder011.html" target="_blank">MVFeeder011</a>     |       50 |          49 |       68 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/MVFeeder015.html" target="_blank">MVFeeder015</a>     |       30 |          29 |       20 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/MVFeeder032.html" target="_blank">MVFeeder032</a>     |       53 |          52 |       40 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/MVFeeder041.html" target="_blank">MVFeeder041</a>     |       88 |          87 |       62 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/MVFeeder063.html" target="_blank">MVFeeder063</a>     |       39 |          38 |       38 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/MVFeeder078.html" target="_blank">MVFeeder078</a>     |       69 |          68 |       46 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/MVFeeder115.html" target="_blank">MVFeeder115</a>     |        4 |           3 |        4 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/MVFeeder128.html" target="_blank">MVFeeder128</a>     |       49 |          48 |       32 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/MVFeeder151.html" target="_blank">MVFeeder151</a>     |       59 |          58 |       44 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/MVFeeder159.html" target="_blank">MVFeeder159</a>     |        8 |           7 |        0 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/MVFeeder176.html" target="_blank">MVFeeder176</a>     |       33 |          32 |       20 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/MVFeeder210.html" target="_blank">MVFeeder210</a>     |      128 |         127 |       82 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/MVFeeder217.html" target="_blank">MVFeeder217</a>     |       44 |          43 |       44 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/MVFeeder232.html" target="_blank">MVFeeder232</a>     |       66 |          65 |       38 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/MVFeeder251.html" target="_blank">MVFeeder251</a>     |      125 |         124 |      106 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/MVFeeder290.html" target="_blank">MVFeeder290</a>     |       12 |          11 |       16 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/MVFeeder312.html" target="_blank">MVFeeder312</a>     |       11 |          10 |        8 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/MVFeeder320.html" target="_blank">MVFeeder320</a>     |       20 |          19 |       12 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| <a href="../_static/Network/MVFeeder339.html" target="_blank">MVFeeder339</a>     |       33 |          32 |       28 |          1 |          1 |                 1 |    'Summer', 'Winter' |

The table is printed using the [Rich Python library](https://rich.readthedocs.io/en/stable/index.html). Links to the
map of each network have been added in the documentation.

There are MV networks whose names start with "MVFeeder" and LV networks whose names with "LVFeeder". For each
network, there are two available load points:

- "Winter": it contains power loads without production.
- "Summer": it contains power loads with production and 20% of the "Winter" load.

The arguments of the method `print_catalogue` can be used to filter the output. If you want to print the LV networks
only, you can call:

```pycon
>>> ElectricalNetwork.print_catalogue(name="LVFeeder")
```

| Name          | Nb buses | Nb branches | Nb loads | Nb sources | Nb grounds | Nb potential refs | Available load points |
| :------------ | -------: | ----------: | -------: | ---------: | ---------: | ----------------: | --------------------: |
| LVFeeder00939 |        8 |           7 |       12 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| LVFeeder02639 |        7 |           6 |       10 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| LVFeeder04790 |        4 |           3 |        4 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| LVFeeder06713 |        3 |           2 |        2 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| LVFeeder06926 |        3 |           2 |        2 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| LVFeeder06975 |        6 |           5 |        8 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| LVFeeder18498 |       18 |          17 |       32 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| LVFeeder18769 |        7 |           6 |       10 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| LVFeeder19558 |        3 |           2 |        2 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| LVFeeder20256 |        9 |           8 |       14 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| LVFeeder23832 |        3 |           2 |        2 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| LVFeeder24400 |        4 |           3 |        4 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| LVFeeder27429 |       11 |          10 |       18 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| LVFeeder27681 |        3 |           2 |        2 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| LVFeeder30216 |        9 |           8 |       14 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| LVFeeder31441 |        4 |           3 |        4 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| LVFeeder36284 |        5 |           4 |        6 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| LVFeeder36360 |        9 |           8 |       14 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| LVFeeder37263 |        3 |           2 |        2 |          1 |          1 |                 1 |    'Summer', 'Winter' |
| LVFeeder38211 |        6 |           5 |        8 |          1 |          1 |                 1 |    'Summer', 'Winter' |

A regular expression can also be used:

```pycon
>>> ElectricalNetwork.print_catalogue(name=r"LVFeeder38[0-9]+")
```

| Name          | Nb buses | Nb branches | Nb loads | Nb sources | Nb grounds | Nb potential refs | Available load points |
| :------------ | -------: | ----------: | -------: | ---------: | ---------: | ----------------: | --------------------: |
| LVFeeder38211 |        6 |           5 |        8 |          1 |          1 |                 1 |    'Summer', 'Winter' |

### Getting an instance

To build a network from the catalogue, the class method `from_catalogue` can be used. The name of the network and
the name of the load point must be provided:

```pycon
>>> en = ElectricalNetwork.from_catalogue(name="LVFeeder38211", load_point_name="Summer")
<ElectricalNetwork: 6 buses, 5 branches, 8 loads, 1 source, 1 ground, 1 potential ref>
```

In case of mistakes, an error is raised:

```pycon
>>> ElectricalNetwork.from_catalogue(name="LVFeeder38211", load_point_name="Unknown")
RoseauLoadFlowException: No load point matching the name 'Unknown' has been found for the network 'LVFeeder38211'.
Please look at the catalogue using the `print_catalogue` class method. [catalogue_not_found]
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

### Printing the catalogue

This catalogue can be printed to the terminal:

```pycon
>>> from roseau.load_flow import TransformerParameters
>>> TransformerParameters.print_catalogue()
```

| Manufacturer | Product range | Efficiency           | Type  | Nominal power (kVA) | High voltage (kV) | Low voltage (kV) |
| :----------- | :------------ | :------------------- | :---- | ------------------: | ----------------: | ---------------: |
| FT           | Standard      | Standard             | Dyn11 |               100.0 |              20.0 |              0.4 |
| FT           | Standard      | Standard             | Dyn11 |               160.0 |              20.0 |              0.4 |
| FT           | Standard      | Standard             | Dyn11 |               250.0 |              20.0 |              0.4 |
| FT           | Standard      | Standard             | Dyn11 |               315.0 |              20.0 |              0.4 |
| FT           | Standard      | Standard             | Dyn11 |               400.0 |              20.0 |              0.4 |
| FT           | Standard      | Standard             | Dyn11 |               500.0 |              20.0 |              0.4 |
| FT           | Standard      | Standard             | Dyn11 |               630.0 |              20.0 |              0.4 |
| FT           | Standard      | Standard             | Dyn11 |               800.0 |              20.0 |              0.4 |
| FT           | Standard      | Standard             | Dyn11 |              1000.0 |              20.0 |              0.4 |
| FT           | Standard      | Standard             | Dyn11 |              1250.0 |              20.0 |              0.4 |
| FT           | Standard      | Standard             | Dyn11 |              1600.0 |              20.0 |              0.4 |
| FT           | Standard      | Standard             | Dyn11 |              2000.0 |              20.0 |              0.4 |
| FT           | Standard      | Standard             | Dyn11 |              2500.0 |              20.0 |              0.4 |
| FT           | Standard      | Standard             | Dyn11 |              3150.0 |              20.0 |              0.4 |
| SE           | Minera        | Standard             | Yzn11 |                50.0 |              20.0 |              0.4 |
| SE           | Minera        | Standard             | Dyn11 |               100.0 |              20.0 |              0.4 |
| SE           | Minera        | Standard             | Dyn11 |               160.0 |              20.0 |              0.4 |
| SE           | Minera        | Standard             | Dyn11 |               250.0 |              20.0 |              0.4 |
| SE           | Minera        | Standard             | Dyn11 |               315.0 |              20.0 |              0.4 |
| SE           | Minera        | Standard             | Dyn11 |               400.0 |              20.0 |              0.4 |
| SE           | Minera        | Standard             | Dyn11 |               500.0 |              20.0 |              0.4 |
| SE           | Minera        | Standard             | Dyn11 |               630.0 |              20.0 |              0.4 |
| SE           | Minera        | Standard             | Dyn11 |               800.0 |              20.0 |              0.4 |
| SE           | Minera        | Standard             | Dyn11 |              1000.0 |              20.0 |              0.4 |
| SE           | Minera        | Standard             | Dyn11 |              1250.0 |              20.0 |              0.4 |
| SE           | Minera        | Standard             | Dyn11 |              1600.0 |              20.0 |              0.4 |
| SE           | Minera        | Standard             | Dyn11 |              2000.0 |              20.0 |              0.4 |
| SE           | Minera        | Standard             | Dyn11 |              2500.0 |              20.0 |              0.4 |
| SE           | Minera        | C0Bk                 | Yzn11 |                50.0 |              20.0 |              0.4 |
| SE           | Minera        | C0Bk                 | Dyn11 |               100.0 |              20.0 |              0.4 |
| SE           | Minera        | C0Bk                 | Dyn11 |               160.0 |              20.0 |              0.4 |
| SE           | Minera        | C0Bk                 | Dyn11 |               250.0 |              20.0 |              0.4 |
| SE           | Minera        | C0Bk                 | Dyn11 |               315.0 |              20.0 |              0.4 |
| SE           | Minera        | C0Bk                 | Dyn11 |               400.0 |              20.0 |              0.4 |
| SE           | Minera        | C0Bk                 | Dyn11 |               500.0 |              20.0 |              0.4 |
| SE           | Minera        | C0Bk                 | Dyn11 |               630.0 |              20.0 |              0.4 |
| SE           | Minera        | C0Bk                 | Dyn11 |               800.0 |              20.0 |              0.4 |
| SE           | Minera        | C0Bk                 | Dyn11 |              1000.0 |              20.0 |              0.4 |
| SE           | Minera        | C0Bk                 | Dyn11 |              1250.0 |              20.0 |              0.4 |
| SE           | Minera        | C0Bk                 | Dyn11 |              1600.0 |              20.0 |              0.4 |
| SE           | Minera        | C0Bk                 | Dyn11 |              2000.0 |              20.0 |              0.4 |
| SE           | Minera        | C0Bk                 | Dyn11 |              2500.0 |              20.0 |              0.4 |
| SE           | Minera        | B0Bk                 | Yzn11 |                50.0 |              20.0 |              0.4 |
| SE           | Minera        | B0Bk                 | Dyn11 |               100.0 |              20.0 |              0.4 |
| SE           | Minera        | B0Bk                 | Dyn11 |               160.0 |              20.0 |              0.4 |
| SE           | Minera        | B0Bk                 | Dyn11 |               250.0 |              20.0 |              0.4 |
| SE           | Minera        | B0Bk                 | Dyn11 |               315.0 |              20.0 |              0.4 |
| SE           | Minera        | B0Bk                 | Dyn11 |               400.0 |              20.0 |              0.4 |
| SE           | Minera        | B0Bk                 | Dyn11 |               500.0 |              20.0 |              0.4 |
| SE           | Minera        | B0Bk                 | Dyn11 |               630.0 |              20.0 |              0.4 |
| SE           | Minera        | B0Bk                 | Dyn11 |               800.0 |              20.0 |              0.4 |
| SE           | Minera        | B0Bk                 | Dyn11 |              1000.0 |              20.0 |              0.4 |
| SE           | Minera        | B0Bk                 | Dyn11 |              1250.0 |              20.0 |              0.4 |
| SE           | Minera        | B0Bk                 | Dyn11 |              1600.0 |              20.0 |              0.4 |
| SE           | Minera        | B0Bk                 | Dyn11 |              2000.0 |              20.0 |              0.4 |
| SE           | Minera        | B0Bk                 | Dyn11 |              2500.0 |              20.0 |              0.4 |
| SE           | Minera        | A0Ak                 | Yzn11 |                50.0 |              20.0 |              0.4 |
| SE           | Minera        | A0Ak                 | Dyn11 |               100.0 |              20.0 |              0.4 |
| SE           | Minera        | A0Ak                 | Dyn11 |               160.0 |              20.0 |              0.4 |
| SE           | Minera        | A0Ak                 | Dyn11 |               250.0 |              20.0 |              0.4 |
| SE           | Minera        | A0Ak                 | Dyn11 |               315.0 |              20.0 |              0.4 |
| SE           | Minera        | A0Ak                 | Dyn11 |               400.0 |              20.0 |              0.4 |
| SE           | Minera        | A0Ak                 | Dyn11 |               500.0 |              20.0 |              0.4 |
| SE           | Minera        | A0Ak                 | Dyn11 |               630.0 |              20.0 |              0.4 |
| SE           | Minera        | A0Ak                 | Dyn11 |               800.0 |              20.0 |              0.4 |
| SE           | Minera        | A0Ak                 | Dyn11 |              1000.0 |              20.0 |              0.4 |
| SE           | Minera        | A0Ak                 | Dyn11 |              1250.0 |              20.0 |              0.4 |
| SE           | Minera        | A0Ak                 | Dyn11 |              1600.0 |              20.0 |              0.4 |
| SE           | Minera        | A0Ak                 | Dyn11 |              2000.0 |              20.0 |              0.4 |
| SE           | Minera        | A0Ak                 | Dyn11 |              2500.0 |              20.0 |              0.4 |
| SE           | Trihal        | Standard             | Dyn11 |               160.0 |              20.0 |              0.4 |
| SE           | Trihal        | Standard             | Dyn11 |               250.0 |              20.0 |              0.4 |
| SE           | Trihal        | Standard             | Dyn11 |               400.0 |              20.0 |              0.4 |
| SE           | Trihal        | Standard             | Dyn11 |               630.0 |              20.0 |              0.4 |
| SE           | Trihal        | Standard             | Dyn11 |               800.0 |              20.0 |              0.4 |
| SE           | Trihal        | Standard             | Dyn11 |              1000.0 |              20.0 |              0.4 |
| SE           | Trihal        | Standard             | Dyn11 |              1250.0 |              20.0 |              0.4 |
| SE           | Trihal        | Standard             | Dyn11 |              1600.0 |              20.0 |              0.4 |
| SE           | Trihal        | Standard             | Dyn11 |              2000.0 |              20.0 |              0.4 |
| SE           | Trihal        | Standard             | Dyn11 |              2500.0 |              20.0 |              0.4 |
| SE           | Trihal        | Reduced_Losses       | Dyn11 |               160.0 |              20.0 |              0.4 |
| SE           | Trihal        | Reduced_Losses       | Dyn11 |               250.0 |              20.0 |              0.4 |
| SE           | Trihal        | Reduced_Losses       | Dyn11 |               400.0 |              20.0 |              0.4 |
| SE           | Trihal        | Reduced_Losses       | Dyn11 |               630.0 |              20.0 |              0.4 |
| SE           | Trihal        | Reduced_Losses       | Dyn11 |               800.0 |              20.0 |              0.4 |
| SE           | Trihal        | Reduced_Losses       | Dyn11 |              1000.0 |              20.0 |              0.4 |
| SE           | Trihal        | Reduced_Losses       | Dyn11 |              1250.0 |              20.0 |              0.4 |
| SE           | Trihal        | Reduced_Losses       | Dyn11 |              1600.0 |              20.0 |              0.4 |
| SE           | Trihal        | Reduced_Losses       | Dyn11 |              2000.0 |              20.0 |              0.4 |
| SE           | Trihal        | Reduced_Losses       | Dyn11 |              2500.0 |              20.0 |              0.4 |
| SE           | Trihal        | Extra_Reduced_Losses | Dyn11 |               160.0 |              20.0 |              0.4 |
| SE           | Trihal        | Extra_Reduced_Losses | Dyn11 |               250.0 |              20.0 |              0.4 |
| SE           | Trihal        | Extra_Reduced_Losses | Dyn11 |               400.0 |              20.0 |              0.4 |
| SE           | Trihal        | Extra_Reduced_Losses | Dyn11 |               630.0 |              20.0 |              0.4 |
| SE           | Trihal        | Extra_Reduced_Losses | Dyn11 |               800.0 |              20.0 |              0.4 |
| SE           | Trihal        | Extra_Reduced_Losses | Dyn11 |              1000.0 |              20.0 |              0.4 |
| SE           | Trihal        | Extra_Reduced_Losses | Dyn11 |              1250.0 |              20.0 |              0.4 |
| SE           | Trihal        | Extra_Reduced_Losses | Dyn11 |              1600.0 |              20.0 |              0.4 |
| SE           | Trihal        | Extra_Reduced_Losses | Dyn11 |              2000.0 |              20.0 |              0.4 |
| SE           | Trihal        | Extra_Reduced_Losses | Dyn11 |              2500.0 |              20.0 |              0.4 |
| SE           | Vegeta        | Standard             | Dyn11 |                50.0 |              20.0 |              0.4 |
| SE           | Vegeta        | Standard             | Dyn11 |               100.0 |              20.0 |              0.4 |
| SE           | Vegeta        | Standard             | Dyn11 |               160.0 |              20.0 |              0.4 |
| SE           | Vegeta        | Standard             | Dyn11 |               250.0 |              20.0 |              0.4 |
| SE           | Vegeta        | Standard             | Dyn11 |               315.0 |              20.0 |              0.4 |
| SE           | Vegeta        | Standard             | Dyn11 |               400.0 |              20.0 |              0.4 |
| SE           | Vegeta        | Standard             | Dyn11 |               500.0 |              20.0 |              0.4 |
| SE           | Vegeta        | Standard             | Dyn11 |               630.0 |              20.0 |              0.4 |
| SE           | Vegeta        | Standard             | Dyn11 |               800.0 |              20.0 |              0.4 |
| SE           | Vegeta        | Standard             | Dyn11 |              1000.0 |              20.0 |              0.4 |
| SE           | Vegeta        | Standard             | Dyn11 |              1250.0 |              20.0 |              0.4 |
| SE           | Vegeta        | Standard             | Dyn11 |              1600.0 |              20.0 |              0.4 |
| SE           | Vegeta        | Standard             | Dyn11 |              2000.0 |              20.0 |              0.4 |
| SE           | Vegeta        | Standard             | Dyn11 |              2500.0 |              20.0 |              0.4 |
| SE           | Vegeta        | Standard             | Dyn11 |              3150.0 |              20.0 |              0.4 |
| SE           | Vegeta        | C0Bk                 | Dyn11 |                50.0 |              20.0 |              0.4 |
| SE           | Vegeta        | C0Bk                 | Dyn11 |               100.0 |              20.0 |              0.4 |
| SE           | Vegeta        | C0Bk                 | Dyn11 |               160.0 |              20.0 |              0.4 |
| SE           | Vegeta        | C0Bk                 | Dyn11 |               250.0 |              20.0 |              0.4 |
| SE           | Vegeta        | C0Bk                 | Dyn11 |               315.0 |              20.0 |              0.4 |
| SE           | Vegeta        | C0Bk                 | Dyn11 |               400.0 |              20.0 |              0.4 |
| SE           | Vegeta        | C0Bk                 | Dyn11 |               500.0 |              20.0 |              0.4 |
| SE           | Vegeta        | C0Bk                 | Dyn11 |               630.0 |              20.0 |              0.4 |
| SE           | Vegeta        | C0Bk                 | Dyn11 |               800.0 |              20.0 |              0.4 |
| SE           | Vegeta        | C0Bk                 | Dyn11 |              1000.0 |              20.0 |              0.4 |
| SE           | Vegeta        | C0Bk                 | Dyn11 |              1250.0 |              20.0 |              0.4 |
| SE           | Vegeta        | C0Bk                 | Dyn11 |              1600.0 |              20.0 |              0.4 |
| SE           | Vegeta        | C0Bk                 | Dyn11 |              2000.0 |              20.0 |              0.4 |
| SE           | Vegeta        | C0Bk                 | Dyn11 |              2500.0 |              20.0 |              0.4 |
| SE           | Vegeta        | C0Bk                 | Dyn11 |              3150.0 |              20.0 |              0.4 |

The following data are available in this table:

- the **manufacturer**: two manufacturers are available. `"SE"` stands for "Schneider-Electric" and `"FT"` stands for
  "France Transfo".
- the product **range** which depends on the manufacturer
- the **efficiency** class of the transformer
- the **type** of the transformer.
- the nominal power, noted **sn**.
- the primary side phase to phase voltage, noted **uhv**.
- the secondary side phase to phase volage, noted **ulv**.

The `print_catalogue` method accepts arguments (in bold above) that can be used to filter the printed table. The
following command only prints transformer parameters of transformers with an efficiency of "A0Ak":

```pycon
>>> TransformerParameters.print_catalogue(efficiency="A0Ak")
```

| Manufacturer | Product range | Efficiency | Type  | Nominal power (kVA) | High voltage (kV) | Low voltage (kV) |
| :----------- | :------------ | :--------- | :---- | ------------------: | ----------------: | ---------------: |
| SE           | Minera        | A0Ak       | Yzn11 |                50.0 |              20.0 |              0.4 |
| SE           | Minera        | A0Ak       | Dyn11 |               100.0 |              20.0 |              0.4 |
| SE           | Minera        | A0Ak       | Dyn11 |               160.0 |              20.0 |              0.4 |
| SE           | Minera        | A0Ak       | Dyn11 |               250.0 |              20.0 |              0.4 |
| SE           | Minera        | A0Ak       | Dyn11 |               315.0 |              20.0 |              0.4 |
| SE           | Minera        | A0Ak       | Dyn11 |               400.0 |              20.0 |              0.4 |
| SE           | Minera        | A0Ak       | Dyn11 |               500.0 |              20.0 |              0.4 |
| SE           | Minera        | A0Ak       | Dyn11 |               630.0 |              20.0 |              0.4 |
| SE           | Minera        | A0Ak       | Dyn11 |               800.0 |              20.0 |              0.4 |
| SE           | Minera        | A0Ak       | Dyn11 |              1000.0 |              20.0 |              0.4 |
| SE           | Minera        | A0Ak       | Dyn11 |              1250.0 |              20.0 |              0.4 |
| SE           | Minera        | A0Ak       | Dyn11 |              1600.0 |              20.0 |              0.4 |
| SE           | Minera        | A0Ak       | Dyn11 |              2000.0 |              20.0 |              0.4 |
| SE           | Minera        | A0Ak       | Dyn11 |              2500.0 |              20.0 |              0.4 |

or only transformers with a wye winding on the primary side (using a regular expression)

```pycon
>>> TransformerParameters.print_catalogue(type=r"^y.*$")
```

| Manufacturer | Product range | Efficiency | Type  | Nominal power (kVA) | High voltage (kV) | Low voltage (kV) |
| :----------- | :------------ | :--------- | :---- | ------------------: | ----------------: | ---------------: |
| SE           | Minera        | Standard   | Yzn11 |                50.0 |              20.0 |              0.4 |
| SE           | Minera        | C0Bk       | Yzn11 |                50.0 |              20.0 |              0.4 |
| SE           | Minera        | B0Bk       | Yzn11 |                50.0 |              20.0 |              0.4 |
| SE           | Minera        | A0Ak       | Yzn11 |                50.0 |              20.0 |              0.4 |

or only transformers meeting both criteria

```pycon
>>> TransformerParameters.print_catalogue(efficiency="A0Ak", type=r"^y.*$")
```

| Manufacturer | Product range | Efficiency | Type  | Nominal power (kVA) | High voltage (kV) | Low voltage (kV) |
| :----------- | :------------ | :--------- | :---- | ------------------: | ----------------: | ---------------: |
| SE           | Minera        | A0Ak       | Yzn11 |                50.0 |              20.0 |              0.4 |

Among all the possible filters, the nominal power and voltages are expected in their default unit (VA and V). The
[Pint](https://pint.readthedocs.io/en/stable/) library can also be used. For instance, if we want to print
transformer parameters with a nominal power of 3150 kVA, the following two commands print the same table:

```pycon
>>> TransformerParameters.print_catalogue(sn=3150e3) # in VA by default

>>> from roseau.load_flow.units import Q_
... TransformerParameters.print_catalogue(sn=Q_(3150, "kVA"))
```

| Manufacturer | Product range | Efficiency | Type  | Nominal power (kVA) | High voltage (kV) | Low voltage (kV) |
| :----------- | :------------ | :--------- | :---- | ------------------: | ----------------: | ---------------: |
| FT           | Standard      | Standard   | Dyn11 |              3150.0 |              20.0 |              0.4 |
| SE           | Vegeta        | Standard   | Dyn11 |              3150.0 |              20.0 |              0.4 |
| SE           | Vegeta        | C0Bk       | Dyn11 |              3150.0 |              20.0 |              0.4 |

### Getting an instance

To build a transformer parameters from the catalogue, the class method `from_catalogue` can be used. The same filter
as the one used for the method `print_catalogue` can be used. The filter must lead to a single transformer in the
catalogue.

For instance, this filter leads to a single transformer parameters in the catalogue:

```pycon
>>> TransformerParameters.from_catalogue(efficiency="A0Ak", type=r"^y.*$")
TransformerParameters(id='SE_Minera_A0Ak_50')
```

In case of mistakes, an error is raised:

```pycon
>>> TransformerParameters.from_catalogue(manufacturer="ft")
RoseauLoadFlowException: Several transformers matching the query ("manufacturer='ft'")
have been found. Please look at the catalogue using the `print_catalogue` class method.
 [catalogue_several_found]
```

or if no results:

```pycon
>>> TransformerParameters.from_catalogue(manufacturer="unknown")
RoseauLoadFlowException: No manufacturer matching the name 'unknown' has been found.
Available manufacturers are 'FT', 'SE'. [catalogue_not_found]
```
