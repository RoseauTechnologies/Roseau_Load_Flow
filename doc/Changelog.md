---
myst:
  html_meta:
    "description lang=en": |
      Release History of Roseau Load Flow - Three-phase unbalanced load flow solver in a Python API by Roseau
      Technologies.
    "description lang=fr": |
      Historique des versions de Roseau Load Flow - Solveur d'écoulement de charge triphasé et déséquilibré dans une
      API Python par Roseau Technologies.
    "keywords lang=fr": version, solveur, simulation, réseau, électrique, bus
    "keywords lang=en": changelog, solver, simulation, distribution grid, bus, model
---

# Changelog

## Version 0.8.0

- {gh-pr}`207` Fix a bug in the zig-zag three-phase transformer model that led to incorrect active power flow in the
  transformer. The bug affected the 50 kVA transformers that have the type `Yzn11` in the catalogue.
- {gh-pr}`206` {gh-issue}`187` Un-deprecate `results_to_dict/json` methods and remove deprecated
  `results_from_dict/json` methods.
- {gh-pr}`205` {gh-issue}`200` Fix error when propagating the potentials from a voltage source with fewer phases
  than the bus.
- {gh-pr}`204` {gh-issue}`193` Remove restrictions on geometry types. Allow specifying the CRS of the geometries.
- {gh-pr}`203` {gh-issue}`186` Detect invalid element overrides when connecting a new element with the
  same ID and type of an existing element.
- {gh-pr}`202` {gh-issue}`188` Explicitly prevent instantiation of abstract classes.
- {gh-pr}`201` {gh-issue}`185` Add `type` attribute to the load classes and rename branches `branch_type`
  attribute to `type` for consistency. Please replace `branch.branch_type` by `branch.type` in your code.
  In addition, loads data frames gained two new columns:
  1. `type` indicating the load type: constant-(`power`, `current`, `impedance`);
  2. and `flexible` indicating if the load is flexible.
- {gh-pr}`197` Fix a bug in three-phase transformer models that led to excessive reactive power flow in the transformer.
- {gh-pr}`199` Add Schneider Electric EcoDesign transformers to the catalogue. These are tagged with the _AA0Ak_
  efficiency class. Other internal data have been added to the catalogue for testing purposes.
- {gh-pr}`198` Simplify the storage of the transformer catalogues. This is an internal change that should not have
  effects on user code.
- {gh-pr}`196` {gh-issue}`194` Improve the error message when accessing `res_flexible_powers` on a non-flexible load
  and relax the flexible parameters plotting methods to accept an array-like of voltages.
- {gh-pr}`195` Use `latexindent.pl` to automatically indent LaTeX files in the documentation.
- {gh-pr}`192` Speed up results access by up to 3x using several optimization techniques. This is especially
  noticeable in timeseries simulations and when accessing results of large networks.
- {gh-pr}`184` Improve the documentation to have a better SEO (sitemap, metadata and canonical URLs). The navigation
  menu has also been improved.
- {gh-pr}`183` {gh-issue}`181` Update the networks catalogue to better represent the real networks.
  LV loads are made single-phase, MV sources are connected in delta, and MV buses lost their neutral.
  Voltage, current, and power limits are added to the buses, lines, and transformers.
  The line parameters IDs are also updated to match the new line parameters catalogue.
- {gh-pr}`182` Improve the error message when trying to access results on the network before running the load flow.
- {gh-pr}`189` Allow flexible loads to have a null active theoretical power.

## Version 0.7.0

```{important}
Starting with version 0.7.0, Roseau Load Flow is no longer supplied as a SaaS. The software is now available as
a standalone Python library.
```

- The documentation is moved from GitHub Pages to <https://www.roseau-load-flow.roseautechnologies.com/>.
- Fix a bug in the engine: it was impossible to change the parameters of center-tapped and single phase transformers.
- {gh-pr}`179` Fix a bug in the propagation of potentials when a center-tapped transformer is used without neutral at
  the primary side.
- {gh-pr}`178` {gh-issue}`176` Merge the `results_to_json`, `results_from_json`, `results_to_dict`
  and `results_from_dict` methods of the `ElectricalNetwork` and `Element`s classes into the methods
  `to_json`, `from_json`, `to_dict` and `from_dict` respectively. The old `results_` methods are
  **deprecated** and will be removed in a future release. The new methods will include the results by
  default, but you can pass `include_results=False` to exclude them.
- {gh-pr}`175` {gh-issue}`174` Fix JSON serialization of network with line parameters created from the
  catalogue.
- {gh-pr}`173` Remove the conda installation option.
- {gh-pr}`168` {gh-issue}`166` Fix initial potentials' propagation.
- {gh-pr}`167` {gh-issue}`161` Add a catalogue of lines using the IEC standards. You can use the method
  `LineParameters.get_catalogue()` to get a data frame of the available lines and the method
  `LineParameters.from_catalogue()` to create a line from the catalogue. Several line types, conductor
  material, and insulation types have been updated. Physical constants have been updated to match the
  IEC standards where applicable.
- {gh-pr}`167` The class `LineParameters` now takes optional arguments `line_type`, `conductor_type`,
  `insulator_type` and `section`. These parameters are accessible as properties. They are filled
  automatically when creating a line from the catalogue or from a geometry.
- {gh-pr}`167` Replace all `print_catalogue()` methods by `get_catalogue()` methods that return a
  data frame instead of printing the catalogue to the console.
- {gh-pr}`167` Enumeration classes no longer have a `from_string` method, you can call the enumeration
  class directly with the string value to get the corresponding enumeration member. Case-insensitive
  behavior is preserved.
- {gh-pr}`167` {gh-issue}`122` Add checks on line height and diameter in the `LineParameters.from_geometry()`
  alternative constructor. This method will try to guess a default conductor and insulation type if
  none is provided.
- {gh-pr}`163` **BREAKING CHANGE:** roseau-load-flow is no longer a SaaS project. Starting with version
  0.7.0, the software is distributed as a standalone Python package. You need a license to use it for
  commercial purposes. See the documentation for more details. This comes with a huge performance
  improvement but requires a breaking change to the API:
  - The `ElectricalNetwork.solve_load_flow()` method no longer takes an `auth` argument.
  - To activate the license, you need to call `roseau.load_flow.activate_license("MY LICENSE KEY")`
    or set the environment variable `ROSEAU_LOAD_FLOW_LICENSE_KEY` (preferred) before calling
    `ElectricalNetwork.solve_load_flow()`. More information in the documentation.
  - Several methods on the `FlexibleParameter` class that previously required `auth` are changed. Make
    sure to follow the documentation to update your code.
- {gh-pr}`163` {gh-issue}`158` Fix `ElectricalNetwork.res_transformers` returning an empty dataframe
  when max_power is not set.
- {gh-pr}`163` Several unused exception codes were removed. An `EMPTY_NETWORK` code was added to indicate
  that a network is being created with no elements.
- {gh-pr}`163` Remove the `ElectricalNetwork.res_info` attribute. `ElectricalNetwork.solve_load_flow()` now
  returns the tuple (number of iterations, residual).
- {gh-pr}`163` Remove the `Bus.clear_short_circuits()` and `ElectricalNetwork.clear_short_circuits()`
  methods. It is currently not possible to clear short-circuits from the network.
- {gh-pr}`163` Improve performance of network creation and results access.
- {gh-pr}`163` Attributes `phases` and `bus` are now read-only on all elements.
- {gh-pr}`151` Require Python 3.10 or newer.

## Version 0.6.0

- {gh-pr}`149` {gh-issue}`145` Add custom pint wrapper for better handling of pint arrays.
- {gh-pr}`148` {gh-issue}`122` deprecate `LineParameters.from_name_lv()` in favor of the more generic
  `LineParameters.from_geometry()`. The method will be removed in a future release.
- {gh-pr}`142` {gh-issue}`136` Add `Bus.res_voltage_unbalance()` method to get the Voltage Unbalance
  Factor (VUF) as defined by the IEC standard IEC 61000-3-14.
- {gh-pr}`141` {gh-issue}`137` Add `ElectricalNetwork.to_graph()` to get a `networkx.Graph` object
  representing the electrical network for graph theory studies. Install with the `"graph"` extra to
  get _networkx_.
  `ElectricalNetwork` also gained a new `buses_clusters` property that returns a list of sets of
  IDs of buses that are connected by a line or a switch. This can be useful to isolate parts of the
  network for localized analysis. For example, to study a LV subnetwork of a MV feeder. Alternatively,
  to get the cluster certain bus belongs to, you can use `Bus.get_connected_buses()`.
- {gh-pr}`141` Add official support for Python 3.12. This is the last release to support Python 3.9.
- {gh-pr}`138` Add network constraints for analysis of the results.
  - Buses can define minimum and maximum voltages. Use `bus.res_violated` to see if the bus has
    over- or under-voltage.
  - Lines can define a maximum current. Use `line.res_violated` to see if the loading of any of the
    line's cables is too high.
  - Transformers can define a maximum power. Use `transformer.res_violated` to see if the transformer
    loading is too high.
  - The new fields also appear in the data frames of the network.
- {gh-pr}`133` {gh-issue}`126` Add Qmin and Qmax limits of flexible parameters.
- {gh-pr}`132` {gh-issue}`101` Document extra utilities including converters and constants.
- {gh-pr}`131` {gh-issue}`127` Improve the documentation of the flexible loads.
  - Add the method `compute_powers` method to the `FlexibleParameter` class to compute the resulting flexible powers
    for a given theoretical power and a list of voltage norms.
  - Add the `plot_control_p`, `plot_control_q` and `plot_pq` methods to the `FlexibleParameter` class to plot the
    control curves and control trajectories.
  - Add the extra `plot` to install `matplotlib` alongside `roseau-load-flow`.
- {gh-pr}`131` Correction of a bug in the error message of the powers setter method.
- {gh-pr}`130` Mark some internal attributes as private, they were previously marked as public.
- {gh-pr}`128` Add the properties `z_line`, `y_shunt` and `with_shunt` to the `Line` class.
- {gh-pr}`125` Speed-up build of conda workflow using mamba.

## Version 0.5.0

- {gh-pr}`121` {gh-issue}`68` Improvements of the `LineParameters` constructor:
  - Delete the `LineModel` class
  - Simplify the `from_dict` method
  - Rename and refactor the method `from_lv_exact` into `from_geometry`.
  - Add documentation for the `LineParameters` alternative constructors.
  - Rename `InsulationType` into `InsulatorType`.
  - Allow the letter "U" for "Underground" line type (only "S" for "Souterrain" in French was accepted). The same
    with the letter "O" for "Overhead" line type (only "A" for "Aérien" in French was accepted).
  - Remove the field `"model"` from the JSON serialization of `LineParameters`.
- {gh-pr}`120` Fix phases of flexible power results.
- {gh-pr}`119` Add explicit error message for singular jacobian.
- {gh-pr}`118` {gh-issue}`95`
  - Add a catalogue of three-phase MV/LV distribution transformers.
  - Remove the class method `TransformerParameters.from_name`.
- {gh-pr}`117` Add prettier to pre-commit
- {gh-pr}`116`
  - Add a catalogue of networks.
  - Add a plotting page to the documentation.
- {gh-pr}`115`
  - Reformat the tutorials in the documentation.
  - Split the "Advanced" tutorial in several smaller files.
  - Remove the Docker installation option.
- {gh-pr}`114` Use Pint >=0.21 to have the percent unit.
- {gh-pr}`113` Raise an error when accessing the results of
  disconnected elements.
- {gh-pr}`112` Make the geometry serialization optional.
- {gh-pr}`106` Improvements for non-euclidean projections.
- {gh-pr}`104` Remove `roseau.load_flow.utils.BranchType`.
- {gh-issue}`99` Add `Line.res_series_currents`
  and `Line.res_shunt_currents` properties to get the currents in the series and shunt components
  of lines. Also added `ElectricalNetwork.res_lines` that contains the series losses and currents
  of all the lines in the network. The property `ElectricalNetwork.res_lines_losses` was removed.
- {gh-issue}`100` Fix the `Yz` transformers.
- {gh-pr}`97` Add the model section to the documentation.
- {gh-pr}`96`
  - Add single-phase transformer.
  - Add center-tapped transformer.
  - Remove the `roseau.load_flow.utils.TransformerType` enumeration.
- {gh-pr}`93` Add short-circuit computation.
- {gh-pr}`92`
  - Add the changelog in the documentation.
  - Use Node.js 20 in the Dockerfile.
  - Correction of a dead link in the README.

## Version 0.4.0

- {gh-pr}`91` Rename `resolution_method` into `solver`.
- {gh-issue}`73` {gh-pr}`85` Rename `precision` into `tolerance` and `final_precision` into `residual`.
- {gh-pr}`82` Add the `"newton_goldstein"` solver.
- {gh-pr}`88` Increase the default `alpha` values for flexible parameters.

## Version 0.3.0

- Every network elements have an `id` which must be unique among the same type of elements.
- The argument `n` (number of ports) have been replaced by a `phase(s)` argument which can be for
  instance `an`, `abc`, `abcn`, `ca`, etc.
- The classes `SimplifiedLine` and `ShuntLine` have been merged into a single class `Line` whose
  behaviour depends on the provided `LineParameters`.
- The classes `DeltaDeltaTransformer`, `DeltaWyeTransformer`, `DeltaZigzagTransformer`,
  `WyeDeltaTransformer`, `WyeWyeTransformer` and `WyeZigzagTransformer` have been replaced by an
  unique `Transformer` class whose behaviour depends on the provided `TransformerParameter`.
- The classes `LineCharacteristics` and `TransformerCharacteristics` have been renamed into
  `LineParameters` and `TransformerParameters`.
- The classes `AdmittanceLoad` and `DeltaAdmittanceLoad` have been removed. Please use
  `ImpedanceLoad` instead, with the desired `phases` argument.
- The classes `DeltaImpedanceLoad` and `DeltaPowerLoad` have been removed. Please use the classes
  `ImpedanceLoad` and `PowerLoad` instead with `phases="abc"`.
- The class `FlexibleLoad` have been removed. Please use the new `flexible_params` argument of the
  `PowerLoad` class constructor.
- The `VoltageSource` is not anymore a subclass of the class `Bus`. It can now be connected to a bus
  just like a load.
- All elements are aware of the network they belong to. It helps the user to avoid mistakes
  (connecting elements from different networks). It also allows showing user warnings when accessing
  to outdated results.
- All properties retrieving results are now prefixed by `res_`.
- Additional results per elements: `res_potentials`, `res_voltages`, `res_series_losses`,
  `res_lie_losses`, etc.
- Pandas Data frame results: now, every result can be retrieved in Pandas Data frame from the
  `ElectricalNetwork` instance. These methods are also prefixed by `res_`.
- Every physical input can be given as quantities (magnitude and unit) using the `Q_` class.
- Every result (except Pandas data frame) are quantities (magnitude and unit).
- Elements can all be serialized as JSON.
- Results of an `ElectricalNetwork` can be serialized as JSON and read from a JSON file.
- The documentation has been improved.

<!-- Local Variables: -->
<!-- mode: gfm -->
<!-- fill-column: 120 -->
<!-- coding: utf-8 -->
<!-- ispell-local-dictionary: "british" -->
<!-- End: -->
