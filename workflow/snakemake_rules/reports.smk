rule build_reports:
    message: "Building summary report tables from fludb and nextclade metadata"
    input:
        db="fludb.db",
        h1_metadata="results/h1n1/ha/metadata.tsv",
        h3_metadata="results/h3n2/ha/metadata.tsv",
        b_metadata="results/vic/ha/metadata.tsv",
        # Ensure all segment exports are complete before generating reports
        auspice_jsons=expand(
            "auspice/{subtype}/{segment}.json",
            subtype=["h3n2", "h1n1", "vic"],
            segment=["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns"]
        )
    output:
        tsv="reports/report.tsv",
        xlsx="reports/report.xlsx"
    log:
        "logs/build_reports.txt"
    shell:
        """
        mkdir -p reports
        python scripts/build-reports.py \
            -i {input.db} \
            -o {output.tsv} \
            -e {output.xlsx} \
            -h1 {input.h1_metadata} \
            -h3 {input.h3_metadata} \
            -b {input.b_metadata} 2>&1 | tee {log}
        """

rule render_reports:
    message: "Rendering HTML report with Quarto"
    input:
        rules.build_reports.output.tsv
    output:
        "reports/render-reports.html"
    log:
        "logs/render_reports.txt"
    shell:
        """
        quarto render scripts/render-reports.qmd \
            --to html \
            --output-dir ../reports/ 2>&1 | tee {log}
        """
