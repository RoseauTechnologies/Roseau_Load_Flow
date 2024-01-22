# Changelog

## Unreleased

- {gh-pr}`168` {gh-issue}`166` Fix initial potentials propagation.
- {gh-pr}`163` {gh-issue}`158` Fix `ElectricalNetwork.res_transformers` returning an empty dataframe
  when max_power is not set.
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
  - Use NodeJs 20 in the Dockerfile.
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
<!-- fill-column: 100 -->
<!-- coding: utf-8 -->
<!-- ispell-local-dictionary: "british" -->
<!-- End: -->
