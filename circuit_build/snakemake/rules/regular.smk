from pathlib import Path
from circuit_build.utils import format_if, write_with_log


rule circuitconfig_base:
    # needed only by spatial_index_segment
    message:
        "Generate CircuitConfig w/o connectome"
    output:
        "CircuitConfig_base",
    log:
        ctx.log_path("circuitconfig_base"),
    run:
        with write_with_log(output[0], log[0]) as out:
            out.write(ctx.build_circuit_config(nrn_path=".", cell_library_file="circuit.mvd3"))


rule circuitconfig_functional:
    message:
        "Generate CircuitConfig for functional circuit"
    input:
        f"sonata/networks/edges/functional/{ctx.EDGE_POPULATION_NAME}/edges.h5",
        f"sonata/networks/nodes/{ctx.NODE_POPULATION_NAME}/nodes.h5",
    output:
        "CircuitConfig",
    log:
        ctx.log_path("circuitconfig_functional"),
    run:
        with write_with_log(output[0], log[0]) as out:
            out.write(
                ctx.build_circuit_config(
                    nrn_path=Path(
                        ctx.CIRCUIT_DIR,
                        f"sonata/networks/edges/functional/{ctx.EDGE_POPULATION_NAME}/edges.h5",
                    ).absolute(),
                    cell_library_file=Path(
                        ctx.CIRCUIT_DIR,
                        f"sonata/networks/nodes/{ctx.NODE_POPULATION_NAME}/nodes.h5",
                    ).absolute(),
                )
            )


rule circuitconfig_structural:
    message:
        "Generate CircuitConfig for structural circuit"
    input:
        f"sonata/networks/edges/structural/{ctx.EDGE_POPULATION_NAME}/edges.h5",
        f"sonata/networks/nodes/{ctx.NODE_POPULATION_NAME}/nodes.h5",
    output:
        "CircuitConfig_struct",
    log:
        ctx.log_path("circuitconfig_structural"),
    run:
        with write_with_log(output[0], log[0]) as out:
            out.write(
                ctx.build_circuit_config(
                    nrn_path=Path(
                        ctx.CIRCUIT_DIR,
                        f"sonata/networks/edges/structural/{ctx.EDGE_POPULATION_NAME}/edges.h5",
                    ).absolute(),
                    cell_library_file=Path(
                        ctx.CIRCUIT_DIR,
                        f"sonata/networks/nodes/{ctx.NODE_POPULATION_NAME}/nodes.h5",
                    ).absolute(),
                )
            )


rule init_cells:
    message:
        "Create an empty cell collection with a correct population name. This collection will be populated further."
    output:
        "circuit.empty.h5",
    log:
        ctx.log_path("init_cells"),
    shell:
        ctx.bbp_env(
            "brainbuilder",
            [
                'echo -n "Using python: " && which python &&',
                'python -c "from voxcell import CellCollection;',
                f"cells = CellCollection('{ctx.NODE_POPULATION_NAME}');",
                "cells.save('{output}');",
                '"',
            ],
        )


rule place_cells:
    message:
        "Generate cell positions; assign me-types"
    input:
        "circuit.empty.h5",
    output:
        "circuit.somata.h5",
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
                ctx.bioname_path("cell_composition.yaml"),
                "--mtype-taxonomy",
                ctx.bioname_path("mtype_taxonomy.tsv"),
                "--atlas",
                ctx.ATLAS,
                "--atlas-cache",
                ctx.ATLAS_CACHE_DIR,
                f"--mini-frequencies {ctx.bioname_path('mini_frequencies.tsv')}"
                if ctx.conf.get(["place_cells", "mini_frequencies"], default=False)
                else "",
                format_if("--region {}", ctx.conf.get(["common", "region"])),
                format_if("--mask {}", ctx.conf.get(["common", "mask"])),
                "--soma-placement",
                ctx.conf.get(["place_cells", "soma_placement"]),
                "--density-factor",
                ctx.conf.get(["place_cells", "density_factor"], default=1.0),
            ]
            + [
                f"--atlas-property {k} {v}"
                for k, v in ctx.conf.get(
                    ["place_cells", "atlas_property"], default={"region": "~brain_regions"}
                ).items()
            ]
            + [
                "--append-hemisphere"
                if ctx.conf.get(["place_cells", "append_hemisphere"], default=False)
                else "",
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
        "circuit.somata.h5",
    output:
        ctx.if_synthesis("axon-morphologies.tsv", "morphologies.tsv"),
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
                ctx.bioname_path("placement_rules.xml"),
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
        cells="circuit.somata.h5",
        morph="morphologies.tsv",
    output:
        "circuit.morphologies.h5",
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
                    func=ctx.bioname_path,
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
        cells="circuit.somata.h5",
        morph="axon-morphologies.tsv",
    output:
        "circuit.synthesized_morphologies.h5",
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
                ctx.bioname_path("tmd_distributions.json"),
                "--tmd-parameters",
                ctx.bioname_path("tmd_parameters.json"),
                "--morph-axon",
                "{input[morph]}",
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
            ],
            slurm_env="synthesize_morphologies",
        )


rule assign_emodels_per_type:
    message:
        "Assign electrical models"
    input:
        "circuit.morphologies.h5",
    output:
        "circuit.{ext}",
    log:
        ctx.log_path("assign_emodels_per_type_{ext}"),
    wildcard_constraints:
        ext="h5|mvd3",
    shell:
        ctx.if_synthesis(
            # FIXME: temporary workaround to skip assign_emodels in synthesis
            "ln -sf {input} {output}",
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
            ),
        )


rule compute_ais_scales:
    message:
        "Add the column @dynamics:ais_scaler to SONATA nodes"
    input:
        "circuit.synthesized_morphologies.h5",
    output:
        "circuit.ais_scales.h5",
    log:
        ctx.log_path("compute_ais_scales"),
    shell:
        ctx.bbp_env(
            "bluepyemodel",
            [
                "BluePyEModel get_me_combos_scales",
                "--cells-path",
                "{input}",
                "--morphology-path",
                ctx.SYNTHESIZE_MORPH_DIR,
                "--release-path",
                ctx.SYNTHESIZE_EMODEL_RELEASE,
                "--output-sonata-path",
                "{output}",
                "--parallel-lib",
                "dask_dataframe",
            ],
            slurm_env="compute_ais_scales",
        )


rule assign_emodels:
    input:
        expand(["circuit.{ext}"], ext=["h5", "mvd3"]),


rule provide_me_info:
    message:
        "Provide MorphoElectrical info for SONATA nodes"
    input:
        "circuit.h5",
    output:
        f"sonata/networks/nodes/{ctx.NODE_POPULATION_NAME}/nodes.h5",
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


rule compute_currents:
    message:
        "Compute currents for SONATA Nodes"
    input:
        "circuit.ais_scales.h5",
    output:
        f"sonata/networks/nodes/{ctx.NODE_POPULATION_NAME}/nodes.h5",
    log:
        ctx.log_path("compute_currents"),
    shell:
        ctx.bbp_env(
            "bluepyemodel",
            [
                "BluePyEModel get_me_combos_currents",
                "--input-sonata-path",
                "{input}",
                "--morphology-path",
                ctx.SYNTHESIZE_MORPH_DIR,
                "--output-sonata-path",
                "{output}",
                "--release-path",
                ctx.SYNTHESIZE_EMODEL_RELEASE,
                "--protocol-config-path",
                ctx.SYNTHESIZE_PROTOCOL_CONFIG,
                "--parallel-lib",
                "dask_dataframe",
            ],
            slurm_env="compute_currents",
        )


rule touchdetector:
    message:
        "Detect touches between neurites"
    input:
        **ctx.if_partition({"nodesets": f"sonata/{ctx.NODESETS_FILE}"}, {}),
        neurons=ctx.if_synthesis(
            "circuit.synthesized_morphologies.h5",
            f"sonata/networks/nodes/{ctx.NODE_POPULATION_NAME}/nodes.h5",
        ),
    output:
        success=touch(f"{ctx.TOUCHES_DIR}{ctx.partition_wildcard()}/_SUCCESS"),
    log:
        ctx.log_path(f"touchdetector{ctx.partition_wildcard()}"),
    params:
        output_dir=lambda wildcards, output: Path(output.success).parent,
    shell:
        ctx.bbp_env(
            "touchdetector",
            [
                "omplace",
                "touchdetector",
                "--output {params.output_dir}",
                "--touchspace",
                ctx.conf.get(["touchdetector", "touchspace"], default="axodendritic"),
                f"--from {{input[neurons]}} {ctx.NODE_POPULATION_NAME}",
                f"--to {{input[neurons]}} {ctx.NODE_POPULATION_NAME}",
                *ctx.if_partition(
                    [
                        "--from-nodeset {input.nodesets} {wildcards.partition}",
                        "--to-nodeset {input.nodesets} {wildcards.partition}",
                    ],
                    [],
                ),
                ctx.BUILDER_RECIPE,
                ctx.if_synthesis(ctx.SYNTHESIZE_MORPH_DIR, ctx.MORPH_RELEASE + "/h5v1/"),
            ],
            slurm_env="touchdetector",
        )


rule touch2parquet:
    message:
        "Convert TouchDetector output to Parquet synapse files"
    input:
        f"{ctx.TOUCHES_DIR}{ctx.partition_wildcard()}/_SUCCESS",
    output:
        parquet_dir=directory(f"{ctx.TOUCHES_DIR}{ctx.partition_wildcard()}/parquet"),
    log:
        ctx.log_path(f"touch2parquet{ctx.partition_wildcard()}"),
    shell:
        "mkdir -p {output.parquet_dir} && " + ctx.bbp_env(
            "parquet-converters",
            ["cd {output.parquet_dir}", "&&", "touch2parquet ../touchesData.*"],
            slurm_env="touch2parquet",
        )


rule spykfunc_s2s:
    message:
        "Convert touches into synapses (S2S)"
    input:
        **ctx.if_partition({"nodesets": f"sonata/{ctx.NODESETS_FILE}"}, {}),
        neurons=ctx.if_synthesis(
            "circuit.synthesized_morphologies.h5",
            f"sonata/networks/nodes/{ctx.NODE_POPULATION_NAME}/nodes.h5",
        ),
        touches=f"{ctx.TOUCHES_DIR}{ctx.partition_wildcard()}/parquet",
    output:
        success=(
            f"connectome/structural/spykfunc{ctx.partition_wildcard()}/circuit.parquet/_SUCCESS"
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
        **ctx.if_partition({"nodesets": f"sonata/{ctx.NODESETS_FILE}"}, {}),
        neurons=ctx.if_synthesis(
            "circuit.synthesized_morphologies.h5",
            f"sonata/networks/nodes/{ctx.NODE_POPULATION_NAME}/nodes.h5",
        ),
        touches=f"{ctx.TOUCHES_DIR}{ctx.partition_wildcard()}/parquet",
    output:
        success=(
            f"connectome/functional/spykfunc{ctx.partition_wildcard()}/circuit.parquet/_SUCCESS"
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
            "connectome/{{connectome_dir}}/spykfunc_{partition}/circuit.parquet/_SUCCESS",
            partition=ctx.PARTITION,
        ),
    output:
        success="connectome/{connectome_dir}/spykfunc/circuit.parquet/_SUCCESS",
    log:
        ctx.log_path("spykfunc_merge_{connectome_dir}"),
    params:
        parquet_dirs=lambda wildcards, input: " ".join(str(Path(i).parent) for i in input),
        output_dir=lambda wildcards, output: Path(output.success).parent.parent,
    shell:
        ctx.run_spykfunc("spykfunc_merge")


rule targetgen:
    message:
        "Generate start.target file"
    input:
        ctx.if_synthesis(
            "circuit.synthesized_morphologies.h5",
            "circuit.h5",
        ),
    output:
        "start.target",
    log:
        ctx.log_path("targetgen"),
    shell:
        ctx.bbp_env(
            "brainbuilder",
            [
                "brainbuilder targets from-input",
                format_if(
                    "--targets {}",
                    value=ctx.conf.get(["targetgen", "targets"]),
                    func=ctx.bioname_path,
                ),
                "--allow-empty"
                if ctx.conf.get(["targetgen", "allow_empty"], default=False)
                else "",
                "--atlas",
                ctx.ATLAS,
                "--atlas-cache",
                ctx.ATLAS_CACHE_DIR,
                "--output {output}",
                "{input}",
            ],
            slurm_env="targetgen",
        )


rule node_sets:
    message:
        "Generate SONATA node sets"
    input:
        ctx.if_synthesis(
            "circuit.synthesized_morphologies.h5",
            f"sonata/networks/nodes/{ctx.NODE_POPULATION_NAME}/nodes.h5",
        ),
    output:
        f"sonata/{ctx.NODESETS_FILE}",
    log:
        ctx.log_path("node_sets"),
    shell:
        ctx.bbp_env(
            "brainbuilder",
            [
                "brainbuilder targets node-sets",
                format_if(
                    "--targets {}",
                    value=ctx.conf.get(["targetgen", "targets"]),
                    func=ctx.bioname_path,
                ),
                "--allow-empty"
                if ctx.conf.get(["targetgen", "allow_empty"], default=False)
                else "",
                "--population",
                ctx.NODE_POPULATION_NAME,
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
        "CircuitConfig_base",
        "circuit.mvd3",
        "start.target",
    output:
        ctx.spatial_index_files("SEGMENT"),
    log:
        ctx.log_path("spatial_index_segment"),
    shell:
        ctx.bbp_env(
            "flatindexer",
            [
                "SDKGenerator CircuitConfig_base segment All SEGMENT",
            ],
            slurm_env="spatial_index_segment",
        )


rule parquet_to_sonata:
    message:
        "Convert synapses from Parquet to SONATA format"
    input:
        "connectome/{connectome_dir}/spykfunc/circuit.parquet/_SUCCESS",
    output:
        "sonata/networks/edges/{connectome_dir}/" + ctx.EDGE_POPULATION_NAME + "/edges.h5",
    log:
        ctx.log_path("parquet_to_sonata_{connectome_dir}"),
    shell:
        ctx.bbp_env(
            "parquet-converters",
            [
                "parquet2hdf5",
                "connectome/{wildcards.connectome_dir}/spykfunc/circuit.parquet/",
                "{output}",
                ctx.EDGE_POPULATION_NAME,
            ],
            slurm_env="parquet_to_sonata",
        )


rule subcellular:
    message:
        "Assign gene expressions / protein concentrations to cells"
    input:
        file="circuit.h5",
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
            out.write(ctx.write_network_config("functional"))


rule circuitconfig_struct_sonata:
    message:
        "Generate SONATA network config (structural)"
    output:
        "sonata/struct_circuit_config.json",
    log:
        ctx.log_path("circuitconfig_struct_sonata"),
    run:
        with write_with_log(output[0], log[0]) as out:
            out.write(ctx.write_network_config("structural"))


rule functional:
    # Note: creating both BlueConfig & circuit_config.json until we're fully transitioned to SONATA
    input:
        "sonata/circuit_config.json",
        f"sonata/networks/nodes/{ctx.NODE_POPULATION_NAME}/nodes.h5",
        f"sonata/{ctx.NODESETS_FILE}",
        f"sonata/networks/edges/functional/{ctx.EDGE_POPULATION_NAME}/edges.h5",
        # for backwards compatibility
        "CircuitConfig",
        "start.target",


rule structural:
    input:
        "sonata/struct_circuit_config.json",
        f"sonata/{ctx.NODESETS_FILE}",
        f"sonata/networks/nodes/{ctx.NODE_POPULATION_NAME}/nodes.h5",
        f"sonata/networks/edges/structural/{ctx.EDGE_POPULATION_NAME}/edges.h5",
        "CircuitConfig_struct",
        "start.target",
