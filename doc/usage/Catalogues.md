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
>>> import roseau.load_flow as rlf
>>> rlf.ElectricalNetwork.get_catalogue()
```

| Name                                                                              | Nb buses | Nb lines | Nb transformers | Nb switches | Nb loads | Nb sources | Nb grounds | Nb potential refs | Available load points |
| :-------------------------------------------------------------------------------- | -------: | -------: | --------------: | ----------: | -------: | ---------: | ---------: | ----------------: | :-------------------- |
| <a href="../_static/Network/LVFeeder00939.html" target="_blank">LVFeeder00939</a> |        8 |        6 |               1 |           0 |       12 |          1 |          1 |                 2 | \['Winter', 'Summer'] |
| <a href="../_static/Network/LVFeeder02639.html" target="_blank">LVFeeder02639</a> |        7 |        5 |               1 |           0 |       10 |          1 |          1 |                 2 | \['Winter', 'Summer'] |
| <a href="../_static/Network/LVFeeder04790.html" target="_blank">LVFeeder04790</a> |        4 |        2 |               1 |           0 |        4 |          1 |          1 |                 2 | \['Winter', 'Summer'] |
| <a href="../_static/Network/LVFeeder06713.html" target="_blank">LVFeeder06713</a> |        3 |        1 |               1 |           0 |        2 |          1 |          1 |                 2 | \['Summer', 'Winter'] |
| <a href="../_static/Network/LVFeeder06926.html" target="_blank">LVFeeder06926</a> |        3 |        1 |               1 |           0 |        2 |          1 |          1 |                 2 | \['Winter', 'Summer'] |
| <a href="../_static/Network/LVFeeder06975.html" target="_blank">LVFeeder06975</a> |        6 |        4 |               1 |           0 |        8 |          1 |          1 |                 2 | \['Winter', 'Summer'] |
| <a href="../_static/Network/LVFeeder18498.html" target="_blank">LVFeeder18498</a> |       18 |       16 |               1 |           0 |       32 |          1 |          1 |                 2 | \['Winter', 'Summer'] |
| <a href="../_static/Network/LVFeeder18769.html" target="_blank">LVFeeder18769</a> |        7 |        5 |               1 |           0 |       10 |          1 |          1 |                 2 | \['Winter', 'Summer'] |
| <a href="../_static/Network/LVFeeder19558.html" target="_blank">LVFeeder19558</a> |        3 |        1 |               1 |           0 |        2 |          1 |          1 |                 2 | \['Winter', 'Summer'] |
| <a href="../_static/Network/LVFeeder20256.html" target="_blank">LVFeeder20256</a> |        9 |        7 |               1 |           0 |       14 |          1 |          1 |                 2 | \['Winter', 'Summer'] |
| <a href="../_static/Network/LVFeeder23832.html" target="_blank">LVFeeder23832</a> |        3 |        1 |               1 |           0 |        2 |          1 |          1 |                 2 | \['Winter', 'Summer'] |
| <a href="../_static/Network/LVFeeder24400.html" target="_blank">LVFeeder24400</a> |        4 |        2 |               1 |           0 |        4 |          1 |          1 |                 2 | \['Summer', 'Winter'] |
| <a href="../_static/Network/LVFeeder27429.html" target="_blank">LVFeeder27429</a> |       11 |        9 |               1 |           0 |       18 |          1 |          1 |                 2 | \['Winter', 'Summer'] |
| <a href="../_static/Network/LVFeeder27681.html" target="_blank">LVFeeder27681</a> |        3 |        1 |               1 |           0 |        2 |          1 |          1 |                 2 | \['Winter', 'Summer'] |
| <a href="../_static/Network/LVFeeder30216.html" target="_blank">LVFeeder30216</a> |        9 |        7 |               1 |           0 |       14 |          1 |          1 |                 2 | \['Summer', 'Winter'] |
| <a href="../_static/Network/LVFeeder31441.html" target="_blank">LVFeeder31441</a> |        4 |        2 |               1 |           0 |        4 |          1 |          1 |                 2 | \['Summer', 'Winter'] |
| <a href="../_static/Network/LVFeeder36284.html" target="_blank">LVFeeder36284</a> |        5 |        3 |               1 |           0 |        6 |          1 |          1 |                 2 | \['Winter', 'Summer'] |
| <a href="../_static/Network/LVFeeder36360.html" target="_blank">LVFeeder36360</a> |        9 |        7 |               1 |           0 |       14 |          1 |          1 |                 2 | \['Summer', 'Winter'] |
| <a href="../_static/Network/LVFeeder37263.html" target="_blank">LVFeeder37263</a> |        3 |        1 |               1 |           0 |        2 |          1 |          1 |                 2 | \['Summer', 'Winter'] |
| <a href="../_static/Network/LVFeeder38211.html" target="_blank">LVFeeder38211</a> |        6 |        4 |               1 |           0 |        8 |          1 |          1 |                 2 | \['Winter', 'Summer'] |
| <a href="../_static/Network/MVFeeder004.html" target="_blank">MVFeeder004</a>     |       17 |       15 |               0 |           1 |       10 |          1 |          1 |                 1 | \['Summer', 'Winter'] |
| <a href="../_static/Network/MVFeeder011.html" target="_blank">MVFeeder011</a>     |       50 |       48 |               0 |           1 |       68 |          1 |          1 |                 1 | \['Summer', 'Winter'] |
| <a href="../_static/Network/MVFeeder015.html" target="_blank">MVFeeder015</a>     |       30 |       28 |               0 |           1 |       20 |          1 |          1 |                 1 | \['Winter', 'Summer'] |
| <a href="../_static/Network/MVFeeder032.html" target="_blank">MVFeeder032</a>     |       53 |       51 |               0 |           1 |       40 |          1 |          1 |                 1 | \['Summer', 'Winter'] |
| <a href="../_static/Network/MVFeeder041.html" target="_blank">MVFeeder041</a>     |       88 |       86 |               0 |           1 |       62 |          1 |          1 |                 1 | \['Winter', 'Summer'] |
| <a href="../_static/Network/MVFeeder063.html" target="_blank">MVFeeder063</a>     |       39 |       37 |               0 |           1 |       38 |          1 |          1 |                 1 | \['Summer', 'Winter'] |
| <a href="../_static/Network/MVFeeder078.html" target="_blank">MVFeeder078</a>     |       69 |       67 |               0 |           1 |       46 |          1 |          1 |                 1 | \['Summer', 'Winter'] |
| <a href="../_static/Network/MVFeeder115.html" target="_blank">MVFeeder115</a>     |        4 |        2 |               0 |           1 |        4 |          1 |          1 |                 1 | \['Summer', 'Winter'] |
| <a href="../_static/Network/MVFeeder128.html" target="_blank">MVFeeder128</a>     |       49 |       47 |               0 |           1 |       32 |          1 |          1 |                 1 | \['Winter', 'Summer'] |
| <a href="../_static/Network/MVFeeder151.html" target="_blank">MVFeeder151</a>     |       59 |       57 |               0 |           1 |       44 |          1 |          1 |                 1 | \['Summer', 'Winter'] |
| <a href="../_static/Network/MVFeeder159.html" target="_blank">MVFeeder159</a>     |        8 |        6 |               0 |           1 |        0 |          1 |          1 |                 1 | \['Summer', 'Winter'] |
| <a href="../_static/Network/MVFeeder176.html" target="_blank">MVFeeder176</a>     |       33 |       31 |               0 |           1 |       20 |          1 |          1 |                 1 | \['Summer', 'Winter'] |
| <a href="../_static/Network/MVFeeder210.html" target="_blank">MVFeeder210</a>     |      128 |      126 |               0 |           1 |       82 |          1 |          1 |                 1 | \['Winter', 'Summer'] |
| <a href="../_static/Network/MVFeeder217.html" target="_blank">MVFeeder217</a>     |       44 |       42 |               0 |           1 |       44 |          1 |          1 |                 1 | \['Winter', 'Summer'] |
| <a href="../_static/Network/MVFeeder232.html" target="_blank">MVFeeder232</a>     |       66 |       64 |               0 |           1 |       38 |          1 |          1 |                 1 | \['Summer', 'Winter'] |
| <a href="../_static/Network/MVFeeder251.html" target="_blank">MVFeeder251</a>     |      125 |      123 |               0 |           1 |      106 |          1 |          1 |                 1 | \['Winter', 'Summer'] |
| <a href="../_static/Network/MVFeeder290.html" target="_blank">MVFeeder290</a>     |       12 |       10 |               0 |           1 |       16 |          1 |          1 |                 1 | \['Winter', 'Summer'] |
| <a href="../_static/Network/MVFeeder312.html" target="_blank">MVFeeder312</a>     |       11 |        9 |               0 |           1 |        8 |          1 |          1 |                 1 | \['Winter', 'Summer'] |
| <a href="../_static/Network/MVFeeder320.html" target="_blank">MVFeeder320</a>     |       20 |       18 |               0 |           1 |       12 |          1 |          1 |                 1 | \['Winter', 'Summer'] |
| <a href="../_static/Network/MVFeeder339.html" target="_blank">MVFeeder339</a>     |       33 |       31 |               0 |           1 |       28 |          1 |          1 |                 1 | \['Summer', 'Winter'] |

There are MV networks whose names start with "MVFeeder" and LV networks whose names with "LVFeeder". For each
network, there are two available load points:

- "Winter": it contains power loads without production.
- "Summer": it contains power loads with production and 20% of the "Winter" load.

The arguments of the method `get_catalogue` can be used to filter the output. If you want to get the LV networks
only, you can call:

```pycon
>>> rlf.ElectricalNetwork.get_catalogue(name=r"LVFeeder.*")
```

| Name          | Nb buses | Nb lines | Nb transformers | Nb switches | Nb loads | Nb sources | Nb grounds | Nb potential refs | Available load points |
| :------------ | -------: | -------: | --------------: | ----------: | -------: | ---------: | ---------: | ----------------: | :-------------------- |
| LVFeeder00939 |        8 |        6 |               1 |           0 |       12 |          1 |          1 |                 2 | \['Winter', 'Summer'] |
| LVFeeder02639 |        7 |        5 |               1 |           0 |       10 |          1 |          1 |                 2 | \['Winter', 'Summer'] |
| LVFeeder04790 |        4 |        2 |               1 |           0 |        4 |          1 |          1 |                 2 | \['Winter', 'Summer'] |
| LVFeeder06713 |        3 |        1 |               1 |           0 |        2 |          1 |          1 |                 2 | \['Summer', 'Winter'] |
| LVFeeder06926 |        3 |        1 |               1 |           0 |        2 |          1 |          1 |                 2 | \['Winter', 'Summer'] |
| LVFeeder06975 |        6 |        4 |               1 |           0 |        8 |          1 |          1 |                 2 | \['Winter', 'Summer'] |
| LVFeeder18498 |       18 |       16 |               1 |           0 |       32 |          1 |          1 |                 2 | \['Winter', 'Summer'] |
| LVFeeder18769 |        7 |        5 |               1 |           0 |       10 |          1 |          1 |                 2 | \['Winter', 'Summer'] |
| LVFeeder19558 |        3 |        1 |               1 |           0 |        2 |          1 |          1 |                 2 | \['Winter', 'Summer'] |
| LVFeeder20256 |        9 |        7 |               1 |           0 |       14 |          1 |          1 |                 2 | \['Winter', 'Summer'] |
| LVFeeder23832 |        3 |        1 |               1 |           0 |        2 |          1 |          1 |                 2 | \['Winter', 'Summer'] |
| LVFeeder24400 |        4 |        2 |               1 |           0 |        4 |          1 |          1 |                 2 | \['Summer', 'Winter'] |
| LVFeeder27429 |       11 |        9 |               1 |           0 |       18 |          1 |          1 |                 2 | \['Winter', 'Summer'] |
| LVFeeder27681 |        3 |        1 |               1 |           0 |        2 |          1 |          1 |                 2 | \['Winter', 'Summer'] |
| LVFeeder30216 |        9 |        7 |               1 |           0 |       14 |          1 |          1 |                 2 | \['Summer', 'Winter'] |
| LVFeeder31441 |        4 |        2 |               1 |           0 |        4 |          1 |          1 |                 2 | \['Summer', 'Winter'] |
| LVFeeder36284 |        5 |        3 |               1 |           0 |        6 |          1 |          1 |                 2 | \['Winter', 'Summer'] |
| LVFeeder36360 |        9 |        7 |               1 |           0 |       14 |          1 |          1 |                 2 | \['Summer', 'Winter'] |
| LVFeeder37263 |        3 |        1 |               1 |           0 |        2 |          1 |          1 |                 2 | \['Summer', 'Winter'] |
| LVFeeder38211 |        6 |        4 |               1 |           0 |        8 |          1 |          1 |                 2 | \['Winter', 'Summer'] |

A regular expression can also be used:

```pycon
>>> rlf.ElectricalNetwork.get_catalogue(name=r"LVFeeder38[0-9]+")
```

| Name          | Nb buses | Nb lines | Nb transformers | Nb switches | Nb loads | Nb sources | Nb grounds | Nb potential refs | Available load points |
| :------------ | -------: | -------: | --------------: | ----------: | -------: | ---------: | ---------: | ----------------: | :-------------------- |
| LVFeeder38211 |        6 |        4 |               1 |           0 |        8 |          1 |          1 |                 2 | \['Winter', 'Summer'] |

### Getting an instance

You can build an `ElectricalNetwork` instance from the catalogue using the class method
`from_catalogue`. The name of the network and the name of the load point must be provided:

```pycon
>>> en = rlf.ElectricalNetwork.from_catalogue(name="LVFeeder38211", load_point_name="Summer")
<ElectricalNetwork: 6 buses, 4 lines, 1 transformer, 0 switches, 8 loads, 1 source, 1 ground, 2 potential refs>
```

In case no or several results match the parameters, an error is raised:

```pycon
>>> rlf.ElectricalNetwork.from_catalogue(name="LVFeeder38211", load_point_name="Unknown")
RoseauLoadFlowException: No load points for network 'LVFeeder38211' matching the query (load_point_name='Unknown')
have been found. Please look at the catalogue using the `get_catalogue` class method. [catalogue_not_found]
```

(catalogues-transformers)=

## Transformers

_Roseau Load Flow_ ships with a catalogue of `TransformerParameters` obtained from data sheets of
real transformers.

### Source of data

The available transformers data come from the following data sheets:

- For _Schneider-Electric EcoDesign_ products (**AA0Ak** efficiency class):
  [Minera](../_static/Transformer/References/2024_03_18_Minera-EcoDesign2021-20kV_ZZ6921.pdf),
  [Vegeta](../_static/Transformer/References/2024_03_18_Vegeta-EcoDesign2021-20kV_ZZ6924.pdf),
  [Trihal](../_static/Transformer/References/2024_03_18_Trihal-EcoDesign2021-20kV_ZZ6925.pdf)
- For _France Transfo_: See
  [this document](../_static/Transformer/References/2023_03_30_Fiche_Technique_France_Transfo.pdf).

All data sheets can be found in the data sheets folder
[on GitHub](https://github.com/RoseauTechnologies/Roseau_Load_Flow/tree/main/doc/_static/Transformer/References)

Pull requests to add other common sources are welcome!

### Inspecting the catalogue

This catalogue can be retrieved in the form of a dataframe using:

```pycon
>>> import roseau.load_flow as rlf
>>> rlf.TransformerParameters.get_catalogue()
```

<!-- Generated with:
    import roseau.load_flow as rlf
    from roseau.load_flow.utils._doc_utils import to_markdown
    tr_catalogue = rlf.TransformerParameters.get_catalogue().sample(30, random_state=1)
    print(to_markdown(tr_catalogue, no_wrap_index=True))
 -->

_Truncated output_

| Name                                                              | Manufacturer | Product range | Efficiency         | Type          | Oil     | Nominal power (kVA) | Vector group | High voltage (kV) | Low voltage (kV) |
| :---------------------------------------------------------------- | :----------- | :------------ | :----------------- | :------------ | :------ | ------------------: | :----------- | ----------------: | ---------------: |
| <nobr>SE Vegeta C0Bk 100kVA 15/20kV(15) 410V Dyn11</nobr>         | SE           | Vegeta        | C0Bk               | three-phase   | ester   |                 100 | Dyn11        |                15 |             0.41 |
| <nobr>SE Vegeta Standard 400kVA 15/20kV(20) 410V Dyn11</nobr>     | SE           | Vegeta        | Standard           | three-phase   | ester   |                 400 | Dyn11        |                20 |             0.41 |
| <nobr>SE Vegeta AA0Ak 630kVA 20kV 410V Dyn11</nobr>               | SE           | Vegeta        | AA0Ak              | three-phase   | ester   |                 630 | Dyn11        |                20 |             0.41 |
| <nobr>SE Minera B0Bk 250kVA 15/20kV(20) 410V Dyn11</nobr>         | SE           | Minera        | B0Bk               | three-phase   | mineral |                 250 | Dyn11        |                20 |             0.41 |
| <nobr>SE Minera Standard 160kVA 15/20kV(15) 410V Dyn11</nobr>     | SE           | Minera        | Standard           | three-phase   | mineral |                 160 | Dyn11        |                15 |             0.41 |
| <nobr>SE Imprego 10kVA 230V 230V Ii0</nobr>                       | SE           | Imprego       |                    | single-phase  | dry     |                  10 | Ii0          |              0.23 |             0.23 |
| <nobr>CA Yellow A0Ak 1250kVA 15.75/21kV(21) 400V Dyn11</nobr>     | CA           | Yellow        | A0Ak               | three-phase   |         |                1250 | Dyn11        |                21 |              0.4 |
| <nobr>SE Trihal AA0Ak 800kVA 15/20kV(15) 410V Dyn11</nobr>        | SE           | Trihal        | AA0Ak              | three-phase   | dry     |                 800 | Dyn11        |                15 |             0.41 |
| <nobr>SE Vegeta C0Bk 100kVA 15/20kV(20) 410V Dyn11</nobr>         | SE           | Vegeta        | C0Bk               | three-phase   | ester   |                 100 | Dyn11        |                20 |             0.41 |
| <nobr>SE Trihal AA0Ak 1000kVA 15/20kV(15) 410V Dyn11</nobr>       | SE           | Trihal        | AA0Ak              | three-phase   | dry     |                1000 | Dyn11        |                15 |             0.41 |
| <nobr>SE Trihal AA0Ak 800kVA 15/20kV(20) 410V Dyn11</nobr>        | SE           | Trihal        | AA0Ak              | three-phase   | dry     |                 800 | Dyn11        |                20 |             0.41 |
| <nobr>SE Minera C0Bk 1600kVA 15/20kV(15) 410V Dyn11</nobr>        | SE           | Minera        | C0Bk               | three-phase   | mineral |                1600 | Dyn11        |                15 |             0.41 |
| <nobr>SE Trihal ExtraReducedLosses 1250kVA 20kV 410V Dyn11</nobr> | SE           | Trihal        | ExtraReducedLosses | three-phase   | dry     |                1250 | Dyn11        |                20 |             0.41 |
| <nobr>SE Minera B0Bk 500kVA 15/20kV(20) 410V Dyn11</nobr>         | SE           | Minera        | B0Bk               | three-phase   | mineral |                 500 | Dyn11        |                20 |             0.41 |
| <nobr>SE Imprego 10kVA 230V 230V Iii0</nobr>                      | SE           | Imprego       |                    | center-tapped | dry     |                  10 | Iii0         |              0.23 |             0.23 |
| <nobr>SE Vegeta C0Bk 400kVA 15/20kV(20) 410V Dyn11</nobr>         | SE           | Vegeta        | C0Bk               | three-phase   | ester   |                 400 | Dyn11        |                20 |             0.41 |
| <nobr>CA Yellow A0Ak 800kVA 15.75/21kV(15.75) 400V Dyn11</nobr>   | CA           | Yellow        | A0Ak               | three-phase   |         |                 800 | Dyn11        |             15.75 |              0.4 |
| <nobr>SE Trihal AA0Ak 2000kVA 15/20kV(20) 410V Dyn11</nobr>       | SE           | Trihal        | AA0Ak              | three-phase   | dry     |                2000 | Dyn11        |                20 |             0.41 |
| <nobr>SE Vegeta C0Bk 1000kVA 15/20kV(20) 410V Dyn11</nobr>        | SE           | Vegeta        | C0Bk               | three-phase   | ester   |                1000 | Dyn11        |                20 |             0.41 |
| <nobr>FT 400kVA 15/20kV(15) 400V Dyn11</nobr>                     | FT           |               |                    | three-phase   | mineral |                 400 | Dyn11        |                15 |              0.4 |
| <nobr>CA Yellow A0Ak 3150kVA 15.75/21kV(15.75) 400V Dyn11</nobr>  | CA           | Yellow        | A0Ak               | three-phase   |         |                3150 | Dyn11        |             15.75 |              0.4 |
| <nobr>FT 2000kVA 15/20kV(20) 400V Dyn11</nobr>                    | FT           |               |                    | three-phase   | mineral |                2000 | Dyn11        |                20 |              0.4 |
| <nobr>CA Yellow A0Ak 400kVA 15.75/21kV(15.75) 400V Dyn11</nobr>   | CA           | Yellow        | A0Ak               | three-phase   |         |                 400 | Dyn11        |             15.75 |              0.4 |
| <nobr>SE Vegeta Standard 800kVA 15/20kV(15) 410V Dyn11</nobr>     | SE           | Vegeta        | Standard           | three-phase   | ester   |                 800 | Dyn11        |                15 |             0.41 |
| <nobr>SE Minera B0Bk 315kVA 15/20kV(15) 410V Dyn11</nobr>         | SE           | Minera        | B0Bk               | three-phase   | mineral |                 315 | Dyn11        |                15 |             0.41 |
| <nobr>SE Minera C0Bk 50kVA 15/20kV(20) 410V Yzn11</nobr>          | SE           | Minera        | C0Bk               | three-phase   | mineral |                  50 | Yzn11        |                20 |             0.41 |
| <nobr>SE Minera C0Bk 630kVA 15/20kV(20) 410V Dyn11</nobr>         | SE           | Minera        | C0Bk               | three-phase   | mineral |                 630 | Dyn11        |                20 |             0.41 |
| <nobr>SE Minera C0Bk 1250kVA 15/20kV(15) 410V Dyn11</nobr>        | SE           | Minera        | C0Bk               | three-phase   | mineral |                1250 | Dyn11        |                15 |             0.41 |
| <nobr>SE Trihal AA0Ak 800kVA 20kV 410V Dyn11</nobr>               | SE           | Trihal        | AA0Ak              | three-phase   | dry     |                 800 | Dyn11        |                20 |             0.41 |
| <nobr>SE Minera B0Bk 2500kVA 15/20kV(20) 410V Dyn11</nobr>        | SE           | Minera        | B0Bk               | three-phase   | mineral |                2500 | Dyn11        |                20 |             0.41 |

The following data are available in this table:

- the **name**: a unique name of the transformer in the catalogue. This is usually a concatenation
  of the manufacturer, the product range, the efficiency class, the nominal power, the high voltage,
  the low voltage, and the vector group.
- the **manufacturer**: these manufacturers are currently available:
  - `"SE"` stands for "Schneider-Electric"
  - `"FT"` stands for "France Transfo"
  - `"CA"` stands for "Cahors"
- the product **range** which depends on the manufacturer
- the **efficiency** class of the transformer. The efficiency class used in the catalogue follows the
  `Eco-Design` requirements as defined by the `EN 50629` standard.
- the **type** of the transfomer. It can be `three-phase`, `single-phase`, or `center-tapped`.
- the oil type of the transformer, noted **oil**:
  - `dry`: dry-type transformer
  - `mineral`: mineral oil immersed transformer
  - `ester`: vegetable oil (natural ester) immersed transformer
- the vector group of the transformer, noted **vg** (e.g., `Dyn11`, `Yzn11`, `Ii0`, etc.)
- the nominal power, noted **sn**.
- the phase-to-phase high voltage, noted **uhv**.
- the no-load phase-to-phase low voltage, noted **ulv**.

The `get_catalogue` method accepts arguments (in bold above) that can be used to filter the returned table. The
following command only retrieves transformer parameters of transformers with an efficiency of "A0Ak":

```pycon
>>> rlf.TransformerParameters.get_catalogue(efficiency="A0Ak")
```

<!-- Generated with:
    import roseau.load_flow as rlf
    from roseau.load_flow.utils._doc_utils import to_markdown
    tr_catalogue = rlf.TransformerParameters.get_catalogue(efficiency="A0Ak").head(10)
    print(to_markdown(tr_catalogue, no_wrap_index=True))
 -->

_Truncated output_

| Name                                                       | Manufacturer | Product range | Efficiency | Type        | Oil     | Nominal power (kVA) | Vector group | High voltage (kV) | Low voltage (kV) |
| :--------------------------------------------------------- | :----------- | :------------ | :--------- | :---------- | :------ | ------------------: | :----------- | ----------------: | ---------------: |
| <nobr>SE Minera A0Ak 50kVA 15/20kV(20) 410V Yzn11</nobr>   | SE           | Minera        | A0Ak       | three-phase | mineral |                  50 | Yzn11        |                20 |             0.41 |
| <nobr>SE Minera A0Ak 100kVA 15/20kV(20) 410V Dyn11</nobr>  | SE           | Minera        | A0Ak       | three-phase | mineral |                 100 | Dyn11        |                20 |             0.41 |
| <nobr>SE Minera A0Ak 160kVA 15/20kV(20) 410V Dyn11</nobr>  | SE           | Minera        | A0Ak       | three-phase | mineral |                 160 | Dyn11        |                20 |             0.41 |
| <nobr>SE Minera A0Ak 250kVA 15/20kV(20) 410V Dyn11</nobr>  | SE           | Minera        | A0Ak       | three-phase | mineral |                 250 | Dyn11        |                20 |             0.41 |
| <nobr>SE Minera A0Ak 315kVA 15/20kV(20) 410V Dyn11</nobr>  | SE           | Minera        | A0Ak       | three-phase | mineral |                 315 | Dyn11        |                20 |             0.41 |
| <nobr>SE Minera A0Ak 400kVA 15/20kV(20) 410V Dyn11</nobr>  | SE           | Minera        | A0Ak       | three-phase | mineral |                 400 | Dyn11        |                20 |             0.41 |
| <nobr>SE Minera A0Ak 500kVA 15/20kV(20) 410V Dyn11</nobr>  | SE           | Minera        | A0Ak       | three-phase | mineral |                 500 | Dyn11        |                20 |             0.41 |
| <nobr>SE Minera A0Ak 630kVA 15/20kV(20) 410V Dyn11</nobr>  | SE           | Minera        | A0Ak       | three-phase | mineral |                 630 | Dyn11        |                20 |             0.41 |
| <nobr>SE Minera A0Ak 800kVA 15/20kV(20) 410V Dyn11</nobr>  | SE           | Minera        | A0Ak       | three-phase | mineral |                 800 | Dyn11        |                20 |             0.41 |
| <nobr>SE Minera A0Ak 1000kVA 15/20kV(20) 410V Dyn11</nobr> | SE           | Minera        | A0Ak       | three-phase | mineral |                1000 | Dyn11        |                20 |             0.41 |

or only transformers with a wye winding on the high voltage side (using a regular expression)

```pycon
>>> rlf.TransformerParameters.get_catalogue(vg=r"Y.*")
```

<!-- Generated with:
    import roseau.load_flow as rlf
    from roseau.load_flow.utils._doc_utils import to_markdown
    tr_catalogue = rlf.TransformerParameters.get_catalogue(vg=r"Y.*").head(10)
    print(to_markdown(tr_catalogue, no_wrap_index=True))
 -->

| Name                                                         | Manufacturer | Product range | Efficiency | Type        | Oil     | Nominal power (kVA) | Vector group | High voltage (kV) | Low voltage (kV) |
| :----------------------------------------------------------- | :----------- | :------------ | :--------- | :---------- | :------ | ------------------: | :----------- | ----------------: | ---------------: |
| <nobr>SE Minera A0Ak 50kVA 15/20kV(20) 410V Yzn11</nobr>     | SE           | Minera        | A0Ak       | three-phase | mineral |                  50 | Yzn11        |                20 |             0.41 |
| <nobr>SE Minera A0Ak 50kVA 15/20kV(15) 410V Yzn11</nobr>     | SE           | Minera        | A0Ak       | three-phase | mineral |                  50 | Yzn11        |                15 |             0.41 |
| <nobr>SE Minera B0Bk 50kVA 15/20kV(20) 410V Yzn11</nobr>     | SE           | Minera        | B0Bk       | three-phase | mineral |                  50 | Yzn11        |                20 |             0.41 |
| <nobr>SE Minera B0Bk 50kVA 15/20kV(15) 410V Yzn11</nobr>     | SE           | Minera        | B0Bk       | three-phase | mineral |                  50 | Yzn11        |                15 |             0.41 |
| <nobr>SE Minera C0Bk 50kVA 15/20kV(20) 410V Yzn11</nobr>     | SE           | Minera        | C0Bk       | three-phase | mineral |                  50 | Yzn11        |                20 |             0.41 |
| <nobr>SE Minera C0Bk 50kVA 15/20kV(15) 410V Yzn11</nobr>     | SE           | Minera        | C0Bk       | three-phase | mineral |                  50 | Yzn11        |                15 |             0.41 |
| <nobr>SE Minera Standard 50kVA 15/20kV(20) 410V Yzn11</nobr> | SE           | Minera        | Standard   | three-phase | mineral |                  50 | Yzn11        |                20 |             0.41 |
| <nobr>SE Minera Standard 50kVA 15/20kV(15) 410V Yzn11</nobr> | SE           | Minera        | Standard   | three-phase | mineral |                  50 | Yzn11        |                15 |             0.41 |

or only transformers meeting both criteria

```pycon
>>> rlf.TransformerParameters.get_catalogue(efficiency="A0Ak", vg=r"Y.*")
```

<!-- Generated with:
    import roseau.load_flow as rlf
    from roseau.load_flow.utils._doc_utils import to_markdown
    tr_catalogue = rlf.TransformerParameters.get_catalogue(efficiency="A0Ak", vg=r"Y.*").head(10)
    print(to_markdown(tr_catalogue, no_wrap_index=True))
 -->

| Name                                                     | Manufacturer | Product range | Efficiency | Type        | Oil     | Nominal power (kVA) | Vector group | High voltage (kV) | Low voltage (kV) |
| :------------------------------------------------------- | :----------- | :------------ | :--------- | :---------- | :------ | ------------------: | :----------- | ----------------: | ---------------: |
| <nobr>SE Minera A0Ak 50kVA 15/20kV(20) 410V Yzn11</nobr> | SE           | Minera        | A0Ak       | three-phase | mineral |                  50 | Yzn11        |                20 |             0.41 |
| <nobr>SE Minera A0Ak 50kVA 15/20kV(15) 410V Yzn11</nobr> | SE           | Minera        | A0Ak       | three-phase | mineral |                  50 | Yzn11        |                15 |             0.41 |

Among all the possible filters, the nominal power and voltages are expected in their default unit
(VA and V). You can also use the [Pint](https://pint.readthedocs.io/en/stable/) library to express
the values in different units. For instance, if you want to get transformer parameters with a
nominal power of 3150 kVA, the following two commands return the same table:

```pycon
>>> import roseau.load_flow as rlf
... rlf.TransformerParameters.get_catalogue(sn=3150e3)  # in VA by default

>>> rlf.TransformerParameters.get_catalogue(sn=rlf.Q_(3150, "kVA"))
```

<!-- Generated with:
    import roseau.load_flow as rlf
    from roseau.load_flow.utils._doc_utils import to_markdown
    tr_catalogue = rlf.TransformerParameters.get_catalogue(sn=rlf.Q_(3150, "kVA")).head(10)
    print(to_markdown(tr_catalogue, no_wrap_index=True))
 -->

| Name                                                           | Manufacturer | Product range | Efficiency | Type        | Oil     | Nominal power (kVA) | Vector group | High voltage (kV) | Low voltage (kV) |
| :------------------------------------------------------------- | :----------- | :------------ | :--------- | :---------- | :------ | ------------------: | :----------- | ----------------: | ---------------: |
| <nobr>FT 3150kVA 15/20kV(20) 400V Dyn11</nobr>                 | FT           |               |            | three-phase | mineral |                3150 | Dyn11        |                20 |              0.4 |
| <nobr>FT 3150kVA 15/20kV(15) 400V Dyn11</nobr>                 | FT           |               |            | three-phase | mineral |                3150 | Dyn11        |                15 |              0.4 |
| <nobr>SE Minera AA0Ak 3150kVA 20kV 410V Dyn11</nobr>           | SE           | Minera        | AA0Ak      | three-phase | mineral |                3150 | Dyn11        |                20 |             0.41 |
| <nobr>SE Trihal AA0Ak 3150kVA 15/20kV(20) 410V Dyn11</nobr>    | SE           | Trihal        | AA0Ak      | three-phase | dry     |                3150 | Dyn11        |                20 |             0.41 |
| <nobr>SE Trihal AA0Ak 3150kVA 15/20kV(15) 410V Dyn11</nobr>    | SE           | Trihal        | AA0Ak      | three-phase | dry     |                3150 | Dyn11        |                15 |             0.41 |
| <nobr>SE Trihal AA0Ak 3150kVA 20kV 410V Dyn11</nobr>           | SE           | Trihal        | AA0Ak      | three-phase | dry     |                3150 | Dyn11        |                20 |             0.41 |
| <nobr>SE Vegeta AA0Ak 3150kVA 20kV 410V Dyn11</nobr>           | SE           | Vegeta        | AA0Ak      | three-phase | ester   |                3150 | Dyn11        |                20 |             0.41 |
| <nobr>SE Vegeta C0Bk 3150kVA 15/20kV(20) 410V Dyn11</nobr>     | SE           | Vegeta        | C0Bk       | three-phase | ester   |                3150 | Dyn11        |                20 |             0.41 |
| <nobr>SE Vegeta C0Bk 3150kVA 15/20kV(15) 410V Dyn11</nobr>     | SE           | Vegeta        | C0Bk       | three-phase | ester   |                3150 | Dyn11        |                15 |             0.41 |
| <nobr>SE Vegeta Standard 3150kVA 15/20kV(20) 410V Dyn11</nobr> | SE           | Vegeta        | Standard   | three-phase | ester   |                3150 | Dyn11        |                20 |             0.41 |

### Getting an instance

You can build a `TransformerParameters` instance from the catalogue using the class method `from_catalogue`.
You must filter the data to get a single transformer. You can apply the same filtering technique used for
the method `get_catalogue` to narrow down the result to a single transformer in the catalogue.

For instance, these parameters filter the catalogue down to a single transformer parameters:

```pycon
>>> rlf.TransformerParameters.from_catalogue(efficiency="A0Ak", vg=r"Y.*", uhv=15000)
<TransformerParameters: id='SE Minera A0Ak 50kVA 15/20kV(15) 410V Yzn11', vg='Yzn11', sn=50000, uhv=15000,
ulv=410, p0=90.0, i0=0.005, psc=750.0, vsc=0.04, manufacturer='SE', range='Minera', efficiency='A0Ak'>
```

The `name` filter can be directly used:

```pycon
>>> rlf.TransformerParameters.from_catalogue(
...     name="SE Minera A0Ak 50kVA 15/20kV(15) 410V Yzn11"
... )
<TransformerParameters: id='SE Minera A0Ak 50kVA 15/20kV(15) 410V Yzn11', vg='Yzn11', sn=50000, uhv=15000,
ulv=410, p0=90.0, i0=0.005, psc=750.0, vsc=0.04, manufacturer='SE', range='Minera', efficiency='A0Ak'>
```

In case no or several results match the parameters, an error is raised:

```pycon
>>> rlf.TransformerParameters.from_catalogue(manufacturer="ft")
RoseauLoadFlowException: Several transformers matching the query (manufacturer='ft') have been found:
'FT 100kVA 15/20kV(20) 400V Dyn11', 'FT 160kVA 15/20kV(20) 400V Dyn11', 'FT 250kVA 15/20kV(20) 400V Dyn11',
'FT 315kVA 15/20kV(20) 400V Dyn11', 'FT 400kVA 15/20kV(20) 400V Dyn11', 'FT 500kVA 15/20kV(20) 400V Dyn11',
'FT 630kVA 15/20kV(20) 400V Dyn11', 'FT 800kVA 15/20kV(20) 400V Dyn11', 'FT 1000kVA 15/20kV(20) 400V Dyn11',
'FT 1250kVA 15/20kV(20) 400V Dyn11', 'FT 1600kVA 15/20kV(20) 400V Dyn11', 'FT 2000kVA 15/20kV(20) 400V Dyn11',
'FT 2500kVA 15/20kV(20) 400V Dyn11', 'FT 3150kVA [...]. [catalogue_several_found]
```

or if no results:

```pycon
>>> rlf.TransformerParameters.from_catalogue(manufacturer="unknown")
RoseauLoadFlowException: No manufacturer matching 'unknown' has been found. Available manufacturers
are 'FT', 'SE', 'CA'. [catalogue_not_found]
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
>>> import roseau.load_flow as rlf
>>> rlf.LineParameters.get_catalogue()
```

_Truncated output_

| Name    | Line type | Phase material | Neutral material | Phase insulator | Neutral insulator | Phase cross-section (mm²) | Neutral cross-section (mm²) | Phase resistance (ohm/km) | Neutral resistance (ohm/km) | Phase reactance (ohm/km) | Neutral reactance (ohm/km) | Phase susceptance (S/km) | Neutral susceptance (S/km) | Phase ampacity (A) | Neutral ampacity (A) |
| :------ | :-------- | :------------- | :--------------- | :-------------- | :---------------- | ------------------------: | --------------------------: | ------------------------: | --------------------------: | -----------------------: | -------------------------: | -----------------------: | -------------------------: | -----------------: | -------------------: |
| O_AL_12 | overhead  | al             | al               |                 |                   |                        12 |                          12 |                      2.69 |                        2.69 |                 0.407632 |                   0.407632 |                2.798e-06 |                  2.798e-06 |                 70 |                   70 |
| O_AL_13 | overhead  | al             | al               |                 |                   |                        13 |                          13 |                     2.495 |                       2.495 |                 0.405118 |                   0.405118 |               2.8161e-06 |                 2.8161e-06 |                 76 |                   76 |
| O_AL_14 | overhead  | al             | al               |                 |                   |                        14 |                          14 |                       2.3 |                         2.3 |                 0.402789 |                   0.402789 |               2.8331e-06 |                 2.8331e-06 |                 82 |                   82 |
| O_AL_19 | overhead  | al             | al               |                 |                   |                        19 |                          19 |                   1.67333 |                     1.67333 |                 0.393195 |                   0.393195 |               2.9051e-06 |                 2.9051e-06 |                103 |                  103 |
| O_AL_20 | overhead  | al             | al               |                 |                   |                        20 |                          20 |                   1.59444 |                     1.59444 |                 0.391584 |                   0.391584 |               2.9175e-06 |                 2.9175e-06 |                106 |                  106 |
| O_AL_22 | overhead  | al             | al               |                 |                   |                        22 |                          22 |                   1.43667 |                     1.43667 |                  0.38859 |                    0.38859 |               2.9409e-06 |                 2.9409e-06 |                113 |                  113 |
| O_AL_25 | overhead  | al             | al               |                 |                   |                        25 |                          25 |                       1.2 |                         1.2 |                 0.384574 |                   0.384574 |                2.973e-06 |                  2.973e-06 |                122 |                  122 |
| O_AL_28 | overhead  | al             | al               |                 |                   |                        28 |                          28 |                    1.1004 |                      1.1004 |                 0.381013 |                   0.381013 |               3.0019e-06 |                 3.0019e-06 |                130 |                  130 |
| O_AL_29 | overhead  | al             | al               |                 |                   |                        29 |                          29 |                    1.0672 |                      1.0672 |                 0.379911 |                   0.379911 |                3.011e-06 |                  3.011e-06 |                132 |                  132 |
| O_AL_33 | overhead  | al             | al               |                 |                   |                        33 |                          33 |                    0.9344 |                      0.9344 |                 0.375852 |                   0.375852 |                3.045e-06 |                  3.045e-06 |                142 |                  142 |
| O_AL_34 | overhead  | al             | al               |                 |                   |                        34 |                          34 |                    0.9012 |                      0.9012 |                 0.374914 |                   0.374914 |               3.0529e-06 |                 3.0529e-06 |                144 |                  144 |
| O_AL_37 | overhead  | al             | al               |                 |                   |                        37 |                          37 |                  0.837733 |                    0.837733 |                 0.372257 |                   0.372257 |               3.0757e-06 |                 3.0757e-06 |                152 |                  152 |
| O_AL_38 | overhead  | al             | al               |                 |                   |                        38 |                          38 |                    0.8226 |                      0.8226 |                  0.37142 |                    0.37142 |               3.0829e-06 |                 3.0829e-06 |                155 |                  155 |
| O_AL_40 | overhead  | al             | al               |                 |                   |                        40 |                          40 |                  0.792333 |                    0.792333 |                 0.369808 |                   0.369808 |               3.0969e-06 |                 3.0969e-06 |                160 |                  160 |
| O_AL_43 | overhead  | al             | al               |                 |                   |                        43 |                          43 |                  0.746933 |                    0.746933 |                 0.367536 |                   0.367536 |               3.1169e-06 |                 3.1169e-06 |                167 |                  167 |
| O_AL_48 | overhead  | al             | al               |                 |                   |                        48 |                          48 |                  0.671267 |                    0.671267 |                  0.36408 |                    0.36408 |               3.1478e-06 |                 3.1478e-06 |                180 |                  180 |
| O_AL_50 | overhead  | al             | al               |                 |                   |                        50 |                          50 |                     0.641 |                       0.641 |                 0.362798 |                   0.362798 |               3.1595e-06 |                 3.1595e-06 |                185 |                  185 |
| O_AL_54 | overhead  | al             | al               |                 |                   |                        54 |                          54 |                    0.6014 |                      0.6014 |                  0.36038 |                    0.36038 |               3.1816e-06 |                 3.1816e-06 |                193 |                  193 |
| O_AL_55 | overhead  | al             | al               |                 |                   |                        55 |                          55 |                    0.5915 |                      0.5915 |                 0.359804 |                   0.359804 |                3.187e-06 |                  3.187e-06 |                195 |                  195 |
| O_AL_59 | overhead  | al             | al               |                 |                   |                        59 |                          59 |                    0.5519 |                      0.5519 |                 0.357598 |                   0.357598 |               3.2075e-06 |                 3.2075e-06 |                203 |                  203 |

The following data are available in this table:

- the **name**. A name that contains the type of the line, the material of the conductor, the
  cross-section area, and optionally the insulator. It is in the form
  `{line_type}_{conductor_material}_{cross_section}_{insulator}`.
- the **line type**. It can be `"OVERHEAD"`, `"UNDERGROUND"` or `"TWISTED"`.
- the **conductor material** for the phases and for the neutral. See the {class}`~roseau.load_flow.Material` class.
- the **insulator** for the phases and for the neutral. See the {class}`~roseau.load_flow.Insulator` class.
- the **cross-section** of the phases and neutral conductors in mm².

in addition to the following calculated physical parameters:

- the _phase resistance_ of the line in ohm/km.
- the _neutral resistance_ of the line in ohm/km.
- the _phase reactance_ of the line in ohm/km.
- the _neutral reactance_ of the line in ohm/km.
- the _phase susceptance_ of the line in S/km.
- the _neutral susceptance_ of the line in S/km.
- the _Phase ampacity_ of the line in A.
- the _neutral ampacity_ of the line in A.

The `get_catalogue` method accepts arguments (in bold above) that can be used to filter the returned
table. The following command only returns line parameters made of Aluminum:

```pycon
>>> rlf.LineParameters.get_catalogue(material="al")
```

_Truncated output_

| Name    | Line type | Phase material | Neutral material | Phase insulator | Neutral insulator | Phase cross-section (mm²) | Neutral cross-section (mm²) | Phase resistance (ohm/km) | Neutral resistance (ohm/km) | Phase reactance (ohm/km) | Neutral reactance (ohm/km) | Phase susceptance (S/km) | Neutral susceptance (S/km) | Phase ampacity (A) | Neutral ampacity (A) |
| :------ | :-------- | :------------- | :--------------- | :-------------- | :---------------- | ------------------------: | --------------------------: | ------------------------: | --------------------------: | -----------------------: | -------------------------: | -----------------------: | -------------------------: | -----------------: | -------------------: |
| O_AL_12 | overhead  | al             | al               |                 |                   |                        12 |                          12 |                      2.69 |                        2.69 |                 0.407632 |                   0.407632 |                2.798e-06 |                  2.798e-06 |                 70 |                   70 |
| O_AL_13 | overhead  | al             | al               |                 |                   |                        13 |                          13 |                     2.495 |                       2.495 |                 0.405118 |                   0.405118 |               2.8161e-06 |                 2.8161e-06 |                 76 |                   76 |
| O_AL_14 | overhead  | al             | al               |                 |                   |                        14 |                          14 |                       2.3 |                         2.3 |                 0.402789 |                   0.402789 |               2.8331e-06 |                 2.8331e-06 |                 82 |                   82 |
| O_AL_19 | overhead  | al             | al               |                 |                   |                        19 |                          19 |                   1.67333 |                     1.67333 |                 0.393195 |                   0.393195 |               2.9051e-06 |                 2.9051e-06 |                103 |                  103 |
| O_AL_20 | overhead  | al             | al               |                 |                   |                        20 |                          20 |                   1.59444 |                     1.59444 |                 0.391584 |                   0.391584 |               2.9175e-06 |                 2.9175e-06 |                106 |                  106 |
| O_AL_22 | overhead  | al             | al               |                 |                   |                        22 |                          22 |                   1.43667 |                     1.43667 |                  0.38859 |                    0.38859 |               2.9409e-06 |                 2.9409e-06 |                113 |                  113 |
| O_AL_25 | overhead  | al             | al               |                 |                   |                        25 |                          25 |                       1.2 |                         1.2 |                 0.384574 |                   0.384574 |                2.973e-06 |                  2.973e-06 |                122 |                  122 |
| O_AL_28 | overhead  | al             | al               |                 |                   |                        28 |                          28 |                    1.1004 |                      1.1004 |                 0.381013 |                   0.381013 |               3.0019e-06 |                 3.0019e-06 |                130 |                  130 |
| O_AL_29 | overhead  | al             | al               |                 |                   |                        29 |                          29 |                    1.0672 |                      1.0672 |                 0.379911 |                   0.379911 |                3.011e-06 |                  3.011e-06 |                132 |                  132 |
| O_AL_33 | overhead  | al             | al               |                 |                   |                        33 |                          33 |                    0.9344 |                      0.9344 |                 0.375852 |                   0.375852 |                3.045e-06 |                  3.045e-06 |                142 |                  142 |

or only lines with a cross-section of 240 mm²

```pycon
>>> rlf.LineParameters.get_catalogue(section=240)
```

| Name     | Line type   | Phase material | Neutral material | Phase insulator | Neutral insulator | Phase cross-section (mm²) | Neutral cross-section (mm²) | Phase resistance (ohm/km) | Neutral resistance (ohm/km) | Phase reactance (ohm/km) | Neutral reactance (ohm/km) | Phase susceptance (S/km) | Neutral susceptance (S/km) | Phase ampacity (A) | Neutral ampacity (A) |
| :------- | :---------- | :------------- | :--------------- | :-------------- | :---------------- | ------------------------: | --------------------------: | ------------------------: | --------------------------: | -----------------------: | -------------------------: | -----------------------: | -------------------------: | -----------------: | -------------------: |
| O_AL_240 | overhead    | al             | al               |                 |                   |                       240 |                         240 |                     0.125 |                       0.125 |                 0.313518 |                   0.313518 |               3.6823e-06 |                 3.6823e-06 |                490 |                  490 |
| O_CU_240 | overhead    | cu             | cu               |                 |                   |                       240 |                         240 |                    0.0775 |                      0.0775 |                 0.313518 |                   0.313518 |               3.6823e-06 |                 3.6823e-06 |                630 |                  630 |
| O_AM_240 | overhead    | am             | am               |                 |                   |                       240 |                         240 |                   0.14525 |                     0.14525 |                 0.313518 |                   0.313518 |               3.6823e-06 |                 3.6823e-06 |                490 |                  490 |
| U_AL_240 | underground | al             | al               |                 |                   |                       240 |                         240 |                     0.125 |                       0.125 |                0.0899296 |                  0.0899296 |              3.69374e-05 |                3.69374e-05 |                428 |                  428 |
| U_CU_240 | underground | cu             | cu               |                 |                   |                       240 |                         240 |                    0.0775 |                      0.0775 |                0.0899296 |                  0.0899296 |              3.69374e-05 |                3.69374e-05 |                549 |                  549 |
| U_AM_240 | underground | am             | am               |                 |                   |                       240 |                         240 |                   0.14525 |                     0.14525 |                0.0899296 |                  0.0899296 |              3.69374e-05 |                3.69374e-05 |                428 |                  428 |
| T_AL_240 | twisted     | al             | al               |                 |                   |                       240 |                         240 |                     0.125 |                       0.125 |                0.0899296 |                  0.0899296 |              3.69374e-05 |                3.69374e-05 |                409 |                  409 |
| T_CU_240 | twisted     | cu             | cu               |                 |                   |                       240 |                         240 |                    0.0775 |                      0.0775 |                0.0899296 |                  0.0899296 |              3.69374e-05 |                3.69374e-05 |                538 |                  538 |
| T_AM_240 | twisted     | am             | am               |                 |                   |                       240 |                         240 |                   0.14525 |                     0.14525 |                0.0899296 |                  0.0899296 |              3.69374e-05 |                3.69374e-05 |                409 |                  409 |

or only lines meeting both criteria

```pycon
>>> rlf.LineParameters.get_catalogue(material="al", section=240)
```

| Name     | Line type   | Phase material | Neutral material | Phase insulator | Neutral insulator | Phase cross-section (mm²) | Neutral cross-section (mm²) | Phase resistance (ohm/km) | Neutral resistance (ohm/km) | Phase reactance (ohm/km) | Neutral reactance (ohm/km) | Phase susceptance (S/km) | Neutral susceptance (S/km) | Phase ampacity (A) | Neutral ampacity (A) |
| :------- | :---------- | :------------- | :--------------- | :-------------- | :---------------- | ------------------------: | --------------------------: | ------------------------: | --------------------------: | -----------------------: | -------------------------: | -----------------------: | -------------------------: | -----------------: | -------------------: |
| O_AL_240 | overhead    | al             | al               |                 |                   |                       240 |                         240 |                     0.125 |                       0.125 |                 0.313518 |                   0.313518 |               3.6823e-06 |                 3.6823e-06 |                490 |                  490 |
| U_AL_240 | underground | al             | al               |                 |                   |                       240 |                         240 |                     0.125 |                       0.125 |                0.0899296 |                  0.0899296 |              3.69374e-05 |                3.69374e-05 |                428 |                  428 |
| T_AL_240 | twisted     | al             | al               |                 |                   |                       240 |                         240 |                     0.125 |                       0.125 |                0.0899296 |                  0.0899296 |              3.69374e-05 |                3.69374e-05 |                409 |                  409 |

When filtering by the cross-section area, it is expected to provide a numeric value in mm² or to use a pint quantity.

### Getting an instance

You can build a `LineParameters` instance from the catalogue using the class method `from_catalogue`.
You must filter the data to get a single line. You can apply the same filtering technique used for
the method `get_catalogue` to narrow down the result to a single line in the catalogue.

For instance, these parameters filter the results down to a single line parameters:

```pycon
>>> rlf.LineParameters.from_catalogue(line_type="underground", material="al", section=240)
LineParameters(id='U_AL_240')
```

Or you can use the `name` filter directly:

```pycon
>>> rlf.LineParameters.from_catalogue(name="U_AL_240")
LineParameters(id='U_AL_240')
```

As you can see, the `id` of the created instance is the same as the name in the catalogue. You can
override this behaviour by passing the `id` parameter to `from_catalogue`:

```pycon
>>> rlf.LineParameters.from_catalogue(name="U_AL_240", id="lp-special")
LineParameters(id='lp-special')
```

Line parameters created from the catalogue are 3-phase without a neutral by default. It is possible
to create line parameters with different numbers of phases using the `nb_phases` parameter.

```pycon
>>> rlf.LineParameters.from_catalogue(name="U_AL_240").z_line.shape
(3, 3)
>>> # For 3-phase with neutral lines
... rlf.LineParameters.from_catalogue(name="U_AL_240", nb_phases=4).z_line.shape
(4, 4)
>>> # For single-phase lines
... rlf.LineParameters.from_catalogue(name="U_AL_240", nb_phases=2).z_line.shape
(2, 2)
```

In case no or several results match the parameters, an error is raised:

```pycon
>>> rlf.LineParameters.from_catalogue(name=r"U_AL.*")
RoseauLoadFlowException: Several line parameters matching the query (name='U_AL.*') have been found:
'U_AL_19', 'U_AL_20', 'U_AL_22', 'U_AL_25', 'U_AL_28', 'U_AL_29', 'U_AL_33', 'U_AL_34', 'U_AL_37',
'U_AL_38', 'U_AL_40', 'U_AL_43', 'U_AL_48', 'U_AL_50', 'U_AL_54', 'U_AL_55', 'U_AL_59', 'U_AL_60',
'U_AL_69', 'U_AL_70', 'U_AL_74', 'U_AL_75', 'U_AL_79', 'U_AL_80', 'U_AL_90', 'U_AL_93', 'U_AL_95',
'U_AL_100', 'U_AL_116', 'U_AL_117', 'U_AL_120', 'U_AL_147', 'U_AL_148', 'U_AL_150', 'U_AL_228',
'U_AL_240', 'U_AL_288'. [catalogue_several_found]
```

or if no results:

```pycon
>>> rlf.LineParameters.from_catalogue(name="unknown")
RoseauLoadFlowException: No name matching 'unknown' has been found. Available names are 'O_AL_12',
'O_AL_13', 'O_AL_14', 'O_AL_19', 'O_AL_20', 'O_AL_22', 'O_AL_25', 'O_AL_28', 'O_AL_29', 'O_AL_33',
'O_AL_34', 'O_AL_37', 'O_AL_38', 'O_AL_40', 'O_AL_43', 'O_AL_48', 'O_AL_50', 'O_AL_54', 'O_AL_55',
'O_AL_59', 'O_AL_60', 'O_AL_69', 'O_AL_70', 'O_AL_74', 'O_AL_75', 'O_AL_79', 'O_AL_80', 'O_AL_90',
'O_AL_93', 'O_AL_95', 'O_AL_100', 'O_AL_116', 'O_AL_117', 'O_AL_120', 'O_AL_147', 'O_AL_148', 'O_AL_150',
'O_AL_228', 'O_AL_240', 'O_AL_288', 'O_CU_3', 'O_CU_7', 'O_CU_12', 'O_CU_13', [...]. [catalogue_not_found]
```
