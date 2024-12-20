import json
from pathlib import Path
from circuit_build.utils import (
    format_dict_to_list,
    format_if,
    if_then_else,
    write_with_log,
)


rule init_cells:
    message:
        "Create an empty cell collection with a correct population name. This collection will be populated further."
    output:
        ctx.paths.auxiliary_path("circuit.empty.h5"),
    log:
        ctx.log_path("init_cells"),
    shell:
        ctx.bbp_env(
            "brainbuilder",
            [
                'echo -n "Using python: " && which python &&',
                'python -c "from voxcell import CellCollection;',
                f"cells = CellCollection('{ctx.nodes_neurons_name}');",
                "cells.save('{output}');",
                '"',
            ],
        )


rule place_cells:
    message:
        "Generate cell positions; assign me-types"
    input:
        ctx.paths.auxiliary_path("circuit.empty.h5"),
    output:
        ctx.paths.auxiliary_path("circuit.somata.h5"),
    log:
        ctx.log_path("place_cells"),
    shell:
        ctx.bbp_env(
            "brainbuilder",
            [
                "brainbuilder cells place",
                "--input",
                "{input}",
                "--composition",
                ctx.paths.bioname_path("cell_composition.yaml"),
                "--mtype-taxonomy",
                ctx.paths.bioname_path("mtype_taxonomy.tsv"),
                "--atlas",
                ctx.ATLAS,
                "--atlas-cache",
                ctx.ATLAS_CACHE_DIR,
                if_then_else(
                    ctx.conf.get(["place_cells", "mini_frequencies"], default=False),
                    f"--mini-frequencies {ctx.paths.bioname_path('mini_frequencies.tsv')}",
                    "",
                ),
                format_if("--region {}", ctx.conf.get(["common", "region"])),
                format_if("--mask {}", ctx.conf.get(["common", "mask"])),
                "--soma-placement",
                ctx.conf.get(["place_cells", "soma_placement"]),
                "--density-factor",
                ctx.conf.get(["place_cells", "density_factor"], default=1.0),
                *format_dict_to_list(
                    "--atlas-property {key} {value}",
                    ctx.conf.get(
                        ["place_cells", "atlas_property"], default={"region": "~brain_regions"}
                    ),
                ),
                if_then_else(
                    ctx.conf.get(["place_cells", "append_hemisphere"], default=False),
                    "--append-hemisphere",
                    "",
                ),
                format_if(
                    "--sort-by {}",
                    value=ctx.conf.get(["place_cells", "sort_by"]),
                    func=lambda x: ",".join(x),
                ),
                "--seed",
                ctx.conf.get(["place_cells", "seed"], default=0),
                "--output",
                "{output}",
            ],
            slurm_env="place_cells",
        )


rule choose_morphologies:
    message:
        "Choose morphologies/axons using 'placement hints' approach"
    input:
        ctx.paths.auxiliary_path("circuit.somata.h5"),
    output:
        ctx.if_synthesis(
            ctx.paths.auxiliary_path("axon-morphologies.tsv"),
            ctx.paths.auxiliary_path("morphologies.tsv"),
        ),
    log:
        ctx.log_path("choose_morphologies"),
    shell:
        ctx.bbp_env(
            "placement-algorithm",
            [
                "choose-morphologies",
                "--cells-path",
                "{input}",
                "--atlas",
                ctx.ATLAS,
                "--atlas-cache",
                ctx.ATLAS_CACHE_DIR,
                "--morphdb",
                ctx.if_synthesis(ctx.SYNTHESIZE_MORPHDB, ctx.MORPHDB),
                "--rules",
                ctx.paths.bioname_path("placement_rules.xml"),
                "--annotations",
                Path(ctx.MORPH_RELEASE, "annotations.json"),
                "--alpha",
                ctx.conf.get(["choose_morphologies", "alpha"]),
                "--seed",
                ctx.conf.get(["choose_morphologies", "seed"], default=0),
                "--output",
                "{output}",
            ]
            + ctx.if_synthesis(
                [
                    "--segment-type",
                    "axon",
                    format_if(
                        "--scales {}",
                        ctx.conf.get(["choose_morphologies", "scales"]),
                        func=lambda x: " ".join(map(str, x)),
                    ),
                ],
                [],
            ),
            slurm_env="choose_morphologies",
        )


rule assign_morphologies:
    message:
        "Assign morphologies"
    input:
        cells=ctx.paths.auxiliary_path("circuit.somata.h5"),
        morph=ctx.paths.auxiliary_path("morphologies.tsv"),
    output:
        ctx.paths.auxiliary_path("circuit.morphologies.h5"),
    log:
        ctx.log_path("assign_morphologies"),
    shell:
        ctx.bbp_env(
            "placement-algorithm",
            [
                "assign-morphologies",
                "--cells-path",
                "{input[cells]}",
                "--morph",
                "{input[morph]}",
                "--atlas",
                ctx.ATLAS,
                "--atlas-cache",
                ctx.ATLAS_CACHE_DIR,
                "--max-drop-ratio",
                ctx.conf.get(["assign_morphologies", "max_drop_ratio"], default=0.0),
                "--seed",
                ctx.conf.get(["assign_morphologies", "seed"], default=0),
                format_if(
                    "--rotations {}",
                    value=ctx.conf.get(["assign_morphologies", "rotations"]),
                    func=ctx.paths.bioname_path,
                ),
                "--out-cells-path",
                "{output}",
            ],
            slurm_env="assign_morphologies",
        )


rule synthesize_morphologies:
    message:
        "Synthesize morphologies"
    input:
        **if_then_else(
            ctx.conf.get(["synthesize_morphologies", "synthesize_axons"], default=False),
            {},
            {"morph": ctx.paths.auxiliary_path("axon-morphologies.tsv")},
        ),
        cells=ctx.paths.auxiliary_path("circuit.somata.h5"),
    output:
        ctx.paths.auxiliary_path("circuit.synthesized_morphologies.h5"),
    log:
        ctx.log_path("synthesize_morphologies"),
    shell:
        ctx.bbp_env(
            "region-grower",
            [
                "region-grower",
                "synthesize-morphologies",
                "--input-cells",
                "{input[cells]}",
                "--atlas",
                ctx.ATLAS,
                "--atlas-cache",
                ctx.ATLAS_CACHE_DIR,
                "--max-drop-ratio",
                ctx.conf.get(["synthesize_morphologies", "max_drop_ratio"], default=0.0),
                "--out-cells",
                "{output}",
                "--tmd-distributions",
                ctx.paths.bioname_path("tmd_distributions.json"),
                "--tmd-parameters",
                ctx.paths.bioname_path("tmd_parameters.json"),
                "--region-structure",
                ctx.paths.bioname_path("region_structure.yaml"),
                if_then_else(
                    ctx.conf.get(["synthesize_morphologies", "synthesize_axons"], default=False),
                    "",
                    "--morph-axon {input[morph]}",
                ),
                "--base-morph-dir",
                Path(ctx.MORPH_RELEASE, "h5v1"),
                "--seed",
                ctx.conf.get(["synthesize_morphologies", "seed"], default=0),
                "--out-apical",
                Path(ctx.SYNTHESIZE_MORPH_DIR, "apical.yaml"),
                "--out-apical-nrn-sections",
                Path(ctx.SYNTHESIZE_MORPH_DIR, "apical_nrn_isec.yaml"),
                "--out-morph-dir",
                ctx.SYNTHESIZE_MORPH_DIR,
                "--max-files-per-dir",
                ctx.conf.get(["synthesize_morphologies", "max_files_per_dir"], default=1024),
                "--out-morph-ext h5",
                "--out-morph-ext asc",
                "--with-mpi",
                format_if(
                    "--scaling-jitter-std {}",
                    ctx.conf.get(["synthesize_morphologies", "scaling_jitter_std"]),
                ),
                format_if(
                    "--rotational-jitter-std {}",
                    ctx.conf.get(["synthesize_morphologies", "rotational_jitter_std"]),
                ),
                format_if(
                    "--out-debug-data {}",
                    ctx.conf.get(["synthesize_morphologies", "out_debug_data"]),
                ),
                format_if(
                    "--log-level {}",
                    ctx.conf.get(["synthesize_morphologies", "log_level"]),
                ),
                if_then_else(
                    ctx.conf.get(["synthesize_morphologies", "synthesize_axons"], default=False),
                    "--synthesize-axons",
                    "",
                ),
            ],
            slurm_env="synthesize_morphologies",
        )


rule assign_emodels:
    message:
        "Assign electrical models"
    input:
        ctx.paths.auxiliary_path("circuit.morphologies.h5"),
    output:
        ctx.paths.auxiliary_path("circuit.h5"),
    log:
        ctx.log_path("assign_emodels_per_type"),
    shell:
        ctx.bbp_env(
            "brainbuilder",
            [
                "brainbuilder cells assign-emodels",
                "--morphdb",
                ctx.MORPHDB,
                "--output {output}",
                "--seed",
                ctx.conf.get(["assign_emodels", "seed"], default=0),
                "{input}",
            ],
            slurm_env="assign_emodels",
        )


rule provide_me_info:
    message:
        "Provide MorphoElectrical info for SONATA nodes"
    input:
        ctx.paths.auxiliary_path("circuit.h5"),
    output:
        ctx.nodes_neurons_file,
    log:
        ctx.log_path("provide_me_info"),
    shell:
        ctx.bbp_env(
            "brainbuilder",
            [
                "brainbuilder sonata provide-me-info",
                format_if("--mecombo-info {}", ctx.EMODEL_RELEASE_MECOMBO),
                "--model-type biophysical",
                "--output {output}",
                "{input}",
            ],
            slurm_env="provide_me_info",
        )


if ctx.NO_EMODEL:

    rule bypass_emodel:
        message:
            "Bypass any emodel related tasks"
        input:
            ctx.paths.auxiliary_path("circuit.synthesized_morphologies.h5"),
        output:
            ctx.nodes_neurons_file,
        log:
            ctx.log_path("bypass_emodel"),
        shell:
            "cp -v {input} {output}"

else:

    rule assign_synthesis_emodels:
        message:
            "Assign emodels for synthesis"
        input:
            ctx.paths.auxiliary_path("circuit.synthesized_morphologies.h5"),
        output:
            ctx.paths.auxiliary_path("circuit.assign_synthesis_emodels.h5"),
        log:
            ctx.log_path("assign_synthesis_emodel"),
        shell:
            ctx.bbp_env(
                "emodel-generalisation",
                [
                    "emodel-generalisation -v assign",
                    "--input-node-path",
                    "{input}",
                    "--config-path",
                    Path(ctx.SYNTHESIZE_EMODEL_RELEASE) / "config",
                    "--output-node-path",
                    "{output}",
                ],
                slurm_env="assign_synthesis_emodels",
            )

    rule adapt_emodels:
        message:
            "Adapt AIS and soma scales and add the column @dynamics:ais_scaler and @dynamics:soma_scale to SONATA nodes"
        input:
            ctx.paths.auxiliary_path("circuit.assign_synthesis_emodels.h5"),
        output:
            ctx.paths.auxiliary_path("circuit.adapt_emodels.h5"),
        log:
            ctx.log_path("adapt_emodels"),
        shell:
            ctx.bbp_env(
                "emodel-generalisation",
                [
                    "emodel-generalisation -v adapt",
                    "--input-node-path",
                    "{input}",
                    "--morphology-path",
                    ctx.SYNTHESIZE_MORPH_DIR,
                    "--config-path",
                    Path(ctx.SYNTHESIZE_EMODEL_RELEASE) / "config",
                    "--output-node-path",
                    "{output}",
                    "--output-hoc-path",
                    ctx.EMODEL_RELEASE_HOC,
                    "--parallel-lib",
                    "dask_dataframe",
                    "--max-scale",
                    3.0,
                    "--min-scale",
                    0.8,
                ],
                slurm_env="adapt_emodels",
            )

    rule compute_currents:
        message:
            "Compute currents for SONATA nodes, assigning the column @dynamics:holding_currents, @dynamics:threshold_currents, @dynamics:resting_potential and @dynamics:input_resistance"
        input:
            ctx.paths.auxiliary_path("circuit.adapt_emodels.h5"),
        output:
            ctx.nodes_neurons_file,
        log:
            ctx.log_path("compute_currents"),
        shell:
            ctx.bbp_env(
                "emodel-generalisation",
                [
                    "emodel-generalisation -v compute_currents",
                    "--input-path",
                    "{input}",
                    "--morphology-path",
                    ctx.SYNTHESIZE_MORPH_DIR,
                    "--output-path",
                    "{output}",
                    "--hoc-path",
                    ctx.EMODEL_RELEASE_HOC,
                    "--parallel-lib",
                    "dask_dataframe",
                ],
                slurm_env="compute_currents",
            )


rule touchdetector:
    message:
        "Detect touches between neurites"
    input:
        circuit_config=ctx.paths.auxiliary_path("circuit_config_hpc.json"),
    output:
        success=touch(
            ctx.tmp_edges_neurons_chemical_connectome_path(
                f"touches{ctx.partition_wildcard()}/raw/_SUCCESS",
            )
        ),
    log:
        ctx.log_path(f"touchdetector{ctx.partition_wildcard()}"),
    params:
        output_dir=lambda wildcards, output: Path(output.success).parent,
    shell:
        ctx.bbp_env(
            "touchdetector",
            [
                "touchdetector",
                "--modern",
                "--circuit-config {input.circuit_config}",
                "--output {params.output_dir}",
                "--touchspace",
                ctx.conf.get(["touchdetector", "touchspace"], default="axodendritic"),
                f"--from {ctx.nodes_neurons_name}",
                f"--to {ctx.nodes_neurons_name}",
                *ctx.if_partition(
                    [
                        "--from-nodeset {wildcards.partition}",
                        "--to-nodeset {wildcards.partition}",
                    ],
                    [],
                ),
                "--recipe",
                ctx.BUILDER_RECIPE,
            ],
            slurm_env="touchdetector",
        )


rule touch2parquet:
    message:
        "Convert TouchDetector output to Parquet synapse files"
    input:
        ctx.tmp_edges_neurons_chemical_connectome_path(
            f"touches{ctx.partition_wildcard()}/raw/_SUCCESS",
        ),
    output:
        parquet_dir=directory(
            ctx.tmp_edges_neurons_chemical_connectome_path(
                f"touches{ctx.partition_wildcard()}/parquet",
            ),
        ),
    log:
        ctx.log_path(f"touch2parquet{ctx.partition_wildcard()}"),
    shell:
        "mkdir -p {output.parquet_dir} && " + ctx.bbp_env(
            "parquet-converters",
            ["cd {output.parquet_dir}", "&&", "touch2parquet ../raw/touchesData.*"],
            slurm_env="touch2parquet",
        )


rule spykfunc_s2s:
    message:
        "Convert touches into synapses (S2S)"
    input:
        **ctx.if_partition({"nodesets": ctx.NODESETS_FILE}, {}),
        neurons=ctx.if_synthesis(
            ctx.paths.auxiliary_path("circuit.synthesized_morphologies.h5"),
            ctx.nodes_neurons_file,
        ),
        touches=ctx.tmp_edges_neurons_chemical_connectome_path(
            f"touches{ctx.partition_wildcard()}/parquet",
        ),
    output:
        success=ctx.tmp_edges_neurons_chemical_connectome_path(
            f"structural/spykfunc{ctx.partition_wildcard()}/circuit.parquet/_SUCCESS",
        ),
    log:
        ctx.log_path(f"spykfunc_s2s{ctx.partition_wildcard()}"),
    params:
        parquet_dirs=lambda wildcards, input: Path(input.touches, "*.parquet"),
        output_dir=lambda wildcards, output: Path(output.success).parent.parent,
    shell:
        ctx.run_spykfunc("spykfunc_s2s")


rule spykfunc_s2f:
    message:
        "Prune touches and convert them into synapses (S2F)"
    input:
        **ctx.if_partition({"nodesets": ctx.NODESETS_FILE}, {}),
        neurons=ctx.if_synthesis(
            ctx.paths.auxiliary_path("circuit.synthesized_morphologies.h5"),
            ctx.nodes_neurons_file,
        ),
        touches=ctx.tmp_edges_neurons_chemical_connectome_path(
            f"touches{ctx.partition_wildcard()}/parquet",
        ),
    output:
        success=ctx.tmp_edges_neurons_chemical_connectome_path(
            f"functional/spykfunc{ctx.partition_wildcard()}/circuit.parquet/_SUCCESS",
        ),
    log:
        ctx.log_path(f"spykfunc_s2f{ctx.partition_wildcard()}"),
    params:
        parquet_dirs=lambda wildcards, input: Path(input.touches, "*.parquet"),
        output_dir=lambda wildcards, output: Path(output.success).parent.parent,
    shell:
        ctx.run_spykfunc("spykfunc_s2f")


rule spykfunc_merge:
    message:
        "Merge synapses from different nodesets."
    input:
        expand(
            ctx.tmp_edges_neurons_chemical_connectome_path(
                "{{connectome_dir}}/spykfunc_{partition}/circuit.parquet/_SUCCESS",
            ),
            partition=ctx.PARTITION,
        ),
    output:
        success=ctx.tmp_edges_neurons_chemical_connectome_path(
            "{connectome_dir}/spykfunc/circuit.parquet/_SUCCESS",
        ),
    log:
        ctx.log_path("spykfunc_merge_{connectome_dir}"),
    params:
        parquet_dirs=lambda wildcards, input: " ".join(str(Path(i).parent) for i in input),
        output_dir=lambda wildcards, output: Path(output.success).parent.parent,
    shell:
        ctx.run_spykfunc("spykfunc_merge")


rule node_sets:
    message:
        "Generate SONATA node sets"
    input:
        ctx.if_synthesis(
            ctx.paths.auxiliary_path("circuit.synthesized_morphologies.h5"),
            ctx.nodes_neurons_file,
        ),
    output:
        ctx.NODESETS_FILE,
    log:
        ctx.log_path("node_sets"),
    shell:
        ctx.bbp_env(
            "brainbuilder",
            [
                "brainbuilder targets node-sets",
                format_if(
                    "--targets {}",
                    value=ctx.conf.get(["node_sets", "targets"]),
                    func=ctx.paths.bioname_path,
                ),
                if_then_else(
                    ctx.conf.get(["node_sets", "allow_empty"], default=False),
                    "--allow-empty",
                    "",
                ),
                "--population",
                ctx.nodes_neurons_name,
                "--atlas",
                ctx.ATLAS,
                "--atlas-cache",
                ctx.ATLAS_CACHE_DIR,
                "--output {output}",
                "{input}",
            ],
            slurm_env="node_sets",
        )


rule spatial_index_segment:
    message:
        "Generate segment spatial index"
    input:
        ctx.nodes_neurons_file,
    output:
        ctx.nodes_spatial_index_success_file,
    log:
        ctx.log_path("spatial_index_segment"),
    shell:
        ctx.bbp_env(
            "spatialindexer",
            [
                "spatial-index-nodes",
                "--verbose",
                "--multi-index",
                "{input}",
                ctx.morphology_path(morphology_type="asc"),
                "-o",
                ctx.nodes_spatial_index_dir,
                "--population",
                ctx.nodes_neurons_name,
            ],
            slurm_env="spatial_index_segment",
        )


rule spatial_index_synapse:
    message:
        "Generate synapse spatial index"
    input:
        ctx.edges_neurons_neurons_file(connectome_type="functional"),
    output:
        ctx.edges_spatial_index_success_file,
        directory(ctx.edges_spatial_index_dir),
    log:
        ctx.log_path("spatial_index_synapse"),
    shell:
        ctx.bbp_env(
            "spatialindexer",
            [
                "spatial-index-synapses",
                "--verbose",
                "--multi-index",
                "{input}",
                "-o",
                ctx.edges_spatial_index_dir,
                "--population",
                ctx.edges_neurons_neurons_name,
            ],
            slurm_env="spatial_index_synapse",
        )


rule parquet_to_sonata:
    message:
        "Convert synapses from Parquet to SONATA format"
    input:
        ctx.tmp_edges_neurons_chemical_connectome_path(
            "{connectome_dir}/spykfunc/circuit.parquet/_SUCCESS",
        ),
    output:
        ctx.edges_neurons_neurons_file(connectome_type="{connectome_dir}"),
    log:
        ctx.log_path("parquet_to_sonata_{connectome_dir}"),
    shell:
        ctx.bbp_env(
            "parquet-converters",
            [
                "parquet2hdf5",
                ctx.tmp_edges_neurons_chemical_connectome_path(
                    "{wildcards.connectome_dir}/spykfunc/circuit.parquet/",
                ),
                "{output}",
                ctx.edges_neurons_neurons_name,
            ],
            slurm_env="parquet_to_sonata",
        )


rule subcellular:
    message:
        "Assign gene expressions / protein concentrations to cells"
    input:
        file=ctx.paths.auxiliary_path("circuit.h5"),
        directory="subcellular",
    output:
        "subcellular.h5",
    log:
        ctx.log_path("subcellular"),
    shell:
        ctx.bbp_env(
            "brainbuilder",
            [
                "brainbuilder subcellular assign",
                "{input[file]}",
                "--subcellular-dir {input[directory]}",
                "--transcriptome {config[subcellular][transcriptome]}",
                "--mtype-taxonomy {config[subcellular][mtype_taxonomy]}",
                "--cell-proteins {config[subcellular][cell_proteins]}",
                "--synapse-proteins {config[subcellular][synapse_proteins]}",
                "--seed {config[subcellular][seed]}",
                "--output {output}",
            ],
            slurm_env="subcellular",
        )


rule circuitconfig_sonata:
    message:
        "Generate SONATA network config"
    output:
        "sonata/circuit_config.json",
    log:
        ctx.log_path("circuitconfig_sonata"),
    run:
        with write_with_log(output[0], log[0]) as out:
            ctx.write_network_config(connectome_dir="functional", output_file=out)



rule circuitconfig_struct_sonata:
    message:
        "Generate SONATA network config (structural)"
    output:
        "sonata/struct_circuit_config.json",
    log:
        ctx.log_path("circuitconfig_struct_sonata"),
    run:
        with write_with_log(output[0], log[0]) as out:
            ctx.write_network_config(connectome_dir="structural", output_file=out)


rule circuitconfig_hpc:
    message:
        "Generate SONATA network config (touchdetector and spykfunc)"
    input:
        **ctx.if_partition({"nodesets": ctx.NODESETS_FILE}, {}),
        neurons=ctx.if_synthesis(
            ctx.paths.auxiliary_path("circuit.synthesized_morphologies.h5"),
            ctx.nodes_neurons_file,
        ),
    output:
        ctx.paths.auxiliary_path("circuit_config_hpc.json"),
    log:
        ctx.log_path("circuitconfig_hpc"),
    run:
        with write_with_log(output[0], log[0]) as out:
            ctx.write_network_config(
                connectome_dir=None,
                output_file=out,
                nodes_file=input.neurons,
                is_partial_config=True,
            )


rule functional:
    input:
        "sonata/circuit_config.json",
        ctx.NODESETS_FILE,
        ctx.nodes_neurons_file,
        ctx.edges_neurons_neurons_file(connectome_type="functional"),
        *ctx.if_no_index(
            [],
            [
                ctx.nodes_spatial_index_success_file,
                ctx.edges_spatial_index_success_file,
            ],
        ),


rule structural:
    input:
        "sonata/struct_circuit_config.json",
        ctx.NODESETS_FILE,
        ctx.nodes_neurons_file,
        ctx.edges_neurons_neurons_file(connectome_type="structural"),
