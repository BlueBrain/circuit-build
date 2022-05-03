

rule ngv_config:
    output:
        "ngv_config.json",
    log:
        ctx.log_path("ngv_config"),
    shell:
        ctx.bbp_env(
            "ngv",
            [
                "ngv config-file",
                "--bioname",
                ctx.BIONAME,
                "--output",
                "{output}",
            ],
        )


rule build_sonata_vasculature:
    input:
        ctx.conf.get(["ngv", "common", "vasculature"]),
    output:
        "sonata/nodes/vasculature.h5",
    log:
        ctx.log_path("build_sonata_vasculature"),
    shell:
        ctx.bbp_env(
            "ngv",
            [
                "vascpy morphology-to-sonata",
                "{input} {output}",
            ],
        )


rule place_glia:
    input:
        "sonata/nodes/vasculature.h5",
    output:
        "sonata.tmp/nodes/glia.somata.h5",
    log:
        ctx.log_path("place_glia"),
    shell:
        ctx.bbp_env(
            "ngv",
            [
                "ngv cell-placement",
                f"--config {ctx.bioname_path('MANIFEST.yaml')}",
                f"--atlas {ctx.conf.get(['ngv', 'common', 'atlas'])}",
                "--atlas-cache .atlas",
                "--vasculature {input}",
                "--output {output}",
                f"--seed {ctx.conf.get(['ngv', 'common', 'seed'])}",
            ],
        )


rule assign_glia_emodels:
    input:
        "sonata.tmp/nodes/glia.somata.h5",
    output:
        "sonata.tmp/nodes/glia.emodels.h5",
    log:
        ctx.log_path("assign_glia_emodels"),
    shell:
        ctx.bbp_env(
            "ngv",
            [
                "ngv assign-emodels",
                "--input {input}",
                "--output {output}",
                f"--hoc {ctx.conf.get(['ngv', 'assign_emodels', 'hoc_template'])}",
            ],
        )


rule finalize_glia:
    input:
        somata="sonata.tmp/nodes/glia.somata.h5",
        emodels="sonata.tmp/nodes/glia.emodels.h5",
    output:
        "sonata/nodes/glia.h5",
    log:
        ctx.log_path("finalize_glia"),
    shell:
        ctx.bbp_env(
            "ngv",
            [
                "ngv finalize-astrocytes",
                "--somata-file {input[somata]}",
                "--emodels-file {input[emodels]}",
                "--output {output}",
            ],
        )


rule build_glia_microdomains:
    input:
        "sonata/nodes/glia.h5",
    output:
        "microdomains.h5",
    log:
        ctx.log_path("build_glia_microdomains"),
    shell:
        ctx.bbp_env(
            "ngv",
            [
                "ngv microdomains",
                f"--config {ctx.bioname_path('MANIFEST.yaml')}",
                "--astrocytes {input}",
                f"--atlas {ctx.conf.get(['ngv', 'common', 'atlas'])}",
                "--atlas-cache .atlas",
                "--output-file-path {output}",
                f"--seed {ctx.conf.get(['ngv', 'common', 'seed'])}",
            ],
        )


rule build_gliovascular_connectivity:
    input:
        astrocytes="sonata/nodes/glia.h5",
        microdomains="microdomains.h5",
        vasculature="sonata/nodes/vasculature.h5",
    output:
        "sonata.tmp/edges/gliovascular.connectivity.h5",
    log:
        ctx.log_path("gliovascular_connectivity"),
    shell:
        ctx.bbp_env(
            "ngv",
            [
                "ngv gliovascular-connectivity",
                f'--config {ctx.bioname_path("MANIFEST.yaml")}',
                "--astrocytes {input[astrocytes]}",
                "--microdomains {input[microdomains]}",
                "--vasculature {input[vasculature]}",
                f"--seed {ctx.conf.get(['ngv', 'common', 'seed'])}",
                "--output {output}",
            ],
        )


rule build_neuroglial_connectivity:
    input:
        astrocytes="sonata/nodes/glia.h5",
        microdomains="microdomains.h5",
    output:
        "sonata.tmp/edges/neuroglial.connectivity.h5",
    log:
        ctx.log_path("neuroglial_connectivity"),
    shell:
        ctx.bbp_env(
            "ngv",
            [
                "ngv neuroglial-connectivity",
                f"--neurons-path {ctx.conf.get(['ngv', 'common', 'base_circuit_cells'])}",
                "--astrocytes-path {input[astrocytes]}",
                "--microdomains-path {input[microdomains]}",
                f"--neuronal-connectivity-path {ctx.conf.get(['ngv', 'common', 'base_circuit_connectome'])}",
                "--output-path {output}",
                f"--seed {ctx.conf.get(['ngv', 'common', 'seed'])}",
            ],
        )


rule build_endfeet_surface_meshes:
    input:
        gliovascular_connectivity="sonata.tmp/edges/gliovascular.connectivity.h5",
    output:
        "endfeet_meshes.h5",
    log:
        ctx.log_path("endfeet_area"),
    shell:
        ctx.bbp_env(
            "ngv",
            [
                "ngv endfeet-area",
                f"--config-path {ctx.bioname_path('MANIFEST.yaml')}",
                f"--vasculature-mesh-path {ctx.conf.get(['ngv', 'common', 'vasculature_mesh'])}",
                "--gliovascular-connectivity-path {input[gliovascular_connectivity]}",
                "--output-path {output}",
                f"--seed {ctx.conf.get(['ngv', 'common', 'seed'])}",
            ],
        )


rule synthesize_glia:
    input:
        astrocytes="sonata/nodes/glia.h5",
        microdomains="microdomains.h5",
        gliovascular_connectivity="sonata.tmp/edges/gliovascular.connectivity.h5",
        neuroglial_connectivity="sonata.tmp/edges/neuroglial.connectivity.h5",
        endfeet_meshes="endfeet_meshes.h5",
    output:
        touch(ctx.SYNTHESIZE_MORPH_DIR + "/_DONE"),
    log:
        ctx.log_path("synthesis"),
    shell:
        ctx.bbp_env(
            "synthesize-glia",
            [
                f"ngv -v synthesis",
                f'--config-path {ctx.bioname_path("MANIFEST.yaml")}',
                f'--tns-distributions-path {ctx.bioname_path("tns_distributions.json")}',
                f'--tns-parameters-path {ctx.bioname_path("tns_parameters.json")}',
                f'--tns-context-path {ctx.bioname_path("tns_context.json")}',
                f'--er-data-path {ctx.bioname_path("er_data.json")}',
                "--astrocytes-path {input[astrocytes]}",
                "--microdomains-path {input[microdomains]}",
                "--gliovascular-connectivity-path {input[gliovascular_connectivity]}",
                "--neuroglial-connectivity-path {input[neuroglial_connectivity]}",
                "--endfeet-meshes-path {input[endfeet_meshes]}",
                f"--neuronal-connectivity-path {ctx.conf.get(['ngv', 'common', 'base_circuit_connectome'])}",
                f"--out-morph-dir {ctx.SYNTHESIZE_MORPH_DIR}",
                ("--parallel" if ctx.conf.get(["ngv", "common", "parallel"]) else ""),
                f"--seed {ctx.conf.get(['ngv', 'common', 'seed'])}",
            ],
            slurm_env="synthesize_glia",
        )


rule finalize_gliovascular_connectivity:
    input:
        astrocytes="sonata/nodes/glia.h5",
        connectivity="sonata.tmp/edges/gliovascular.connectivity.h5",
        endfeet_meshes="endfeet_meshes.h5",
        morphologies=ctx.SYNTHESIZE_MORPH_DIR + "/_DONE",
        vasculature_sonata="sonata/nodes/vasculature.h5",
    output:
        "sonata/edges/gliovascular.h5",
    log:
        ctx.log_path("finalize_gliovascular_connectivity"),
    shell:
        ctx.bbp_env(
            "ngv",
            [
                "ngv attach-endfeet-info-to-gliovascular-connectivity",
                "--input-file {input[connectivity]}",
                "--output-file {output}",
                "--astrocytes {input[astrocytes]}",
                "--endfeet-meshes-path {input[endfeet_meshes]}",
                "--vasculature-sonata {input[vasculature_sonata]}",
                f"--morph-dir {ctx.SYNTHESIZE_MORPH_DIR}",
                ("--parallel" if ctx.conf.get(["ngv", "common", "parallel"]) else ""),
                f"--seed {ctx.conf.get(['ngv', 'common', 'seed'])}",
            ],
        )


rule finalize_neuroglial_connectivity:
    input:
        astrocytes="sonata/nodes/glia.h5",
        microdomains="microdomains.h5",
        connectivity="sonata.tmp/edges/neuroglial.connectivity.h5",
        morphologies=ctx.SYNTHESIZE_MORPH_DIR + "/_DONE",
    output:
        "sonata/edges/neuroglial.h5",
    log:
        ctx.log_path("finalize_neuroglial_connectivity"),
    shell:
        ctx.bbp_env(
            "ngv",
            [
                "ngv attach-morphology-info-to-neuroglial-connectivity",
                "--input-file-path {input[connectivity]}",
                "--output-file-path {output}",
                "--astrocytes-path {input[astrocytes]}",
                "--microdomains-path {input[microdomains]}",
                f"--synaptic-data-path {ctx.conf.get(['ngv', 'common', 'base_circuit_connectome'])}",
                f"--morph-dir {ctx.SYNTHESIZE_MORPH_DIR}",
                ("--parallel" if ctx.conf.get(["ngv", "common", "parallel"]) else ""),
                f"--seed {ctx.conf.get(['ngv', 'common', 'seed'])}",
            ],
        )


rule glial_gap_junctions:
    message:
        "Detect touches between astrocytes"
    input:
        astrocytes="sonata/nodes/glia.h5",
        morphologies=ctx.SYNTHESIZE_MORPH_DIR + "/_DONE",
    output:
        touch(ctx.TOUCHES_GLIA_DIR + "/_SUCCESS"),
    log:
        ctx.log_path("glial_gap_junctions"),
    shell:
        ctx.bbp_env(
            "ngv-touchdetector",
            [
                "touchdetector",
                f"--output {ctx.TOUCHES_GLIA_DIR}",
                "--save-state",
                "--from {input[astrocytes]} astrocytes",
                "--to {input[astrocytes]} astrocytes",
                ctx.bioname_path("astrocyte_gap_junction_recipe.xml"),
                ctx.SYNTHESIZE_MORPH_DIR,
            ],
            slurm_env="ngv-touchdetector",
        )


rule glialglial_connectivity:
    message:
        "Extract glial glial connectivity from touches"
    input:
        astrocytes="sonata/nodes/glia.h5",
        touches=ctx.TOUCHES_GLIA_DIR + "/_SUCCESS",
    output:
        glialglial_connectivity="sonata/edges/glialglial.h5",
    log:
        ctx.log_path("glialglial_connectivity"),
    shell:
        ctx.bbp_env(
            "ngv",
            [
                "ngv glialglial-connectivity",
                "--astrocytes {input[astrocytes]}",
                f"--touches-dir {ctx.TOUCHES_GLIA_DIR}",
                "--output-connectivity {output[glialglial_connectivity]}",
                f"--seed {ctx.conf.get(['ngv', 'common', 'seed'])}",
            ],
        )


rule ngv:
    input:
        "ngv_config.json",
        "sonata/nodes/vasculature.h5",
        "sonata/nodes/glia.h5",
        "microdomains.h5",
        "sonata/edges/neuroglial.h5",
        "sonata/edges/gliovascular.h5",
        "sonata/edges/glialglial.h5",
        "endfeet_meshes.h5",
        ctx.SYNTHESIZE_MORPH_DIR + "/_DONE",
        ctx.TOUCHES_GLIA_DIR + "/_SUCCESS",
