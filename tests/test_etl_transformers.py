from etl.transformers.alleles import parse_allele_records
from etl.transformers.diplotypes import parse_diplotype_records
from etl.transformers.recommendations import RecommendationCondition, parse_recommendation_records


def test_parse_allele_records_maps_functionality_and_activity_value():
    raw = [
        {
            "genesymbol": "CYP2C19",
            "name": "*1",
            "functionalstatus": None,
            "clinicalfunctionalstatus": "Normal function",
            "activityvalue": None,
        },
        {
            "genesymbol": "CYP2D6",
            "name": "*9",
            "functionalstatus": None,
            "clinicalfunctionalstatus": "Decreased function",
            "activityvalue": "0.25",
        },
        {
            "genesymbol": "CYP2D6",
            "name": "*95",
            "functionalstatus": None,
            "clinicalfunctionalstatus": "Uncertain function",
            "activityvalue": "n/a",
        },
    ]

    records = parse_allele_records(raw)

    assert len(records) == 3
    assert records[0].star_allele == "*1"
    assert records[0].functionality == "Normal function"
    assert records[0].activity_value is None
    assert records[1].activity_value == 0.25
    assert records[2].activity_value is None


def test_parse_allele_records_skips_rows_without_a_name():
    raw = [{"genesymbol": "CYP2C19", "name": None, "clinicalfunctionalstatus": "Normal function"}]

    assert parse_allele_records(raw) == []


def test_parse_diplotype_records_splits_diplotype_and_prefixes_phenotype():
    raw = [
        {
            "genesymbol": "CYP2C19",
            "diplotype": "*1/*17",
            "totalactivityscore": "n/a",
            "generesult": "Rapid Metabolizer",
            "description": "An individual carrying one normal function allele and one increased "
            "function allele",
        }
    ]

    records = parse_diplotype_records(raw, "CYP2C19")

    assert len(records) == 1
    record = records[0]
    assert record.allele1 == "*1"
    assert record.allele2 == "*17"
    assert record.activity_score is None
    assert record.phenotype_name == "CYP2C19 Rapid Metabolizer"
    assert record.phenotype_description.startswith("An individual")


def test_parse_diplotype_records_skips_malformed_rows():
    raw = [
        {"genesymbol": "CYP2C19", "diplotype": None, "generesult": "Rapid Metabolizer"},
        {"genesymbol": "CYP2C19", "diplotype": "*1", "generesult": "Rapid Metabolizer"},
        {"genesymbol": "CYP2C19", "diplotype": "*1/*17", "generesult": None},
    ]

    assert parse_diplotype_records(raw, "CYP2C19") == []


def test_parse_recommendation_records_extracts_conditions_and_prefixes_population():
    raw = [
        {
            "drugrecommendation": "If considering clopidogrel, use at standard dose (75 mg/day)",
            "implications": {
                "CYP2C19": "Increased clopidogrel active metabolite formation; "
                "lower on-treatment platelet reactivity"
            },
            "classification": "Strong",
            "phenotypes": {"CYP2C19": "Ultrarapid Metabolizer"},
            "population": "CVI ACS PCI",
        }
    ]

    records = parse_recommendation_records(raw, guideline_version="70")

    assert len(records) == 1
    record = records[0]
    assert record.recommendation_text.startswith("[CVI ACS PCI]")
    assert record.classification == "Strong"
    assert record.cpic_guideline_version == "70"
    expected_phenotype = "CYP2C19 Ultrarapid Metabolizer"
    assert record.conditions == [
        RecommendationCondition(gene_symbol="CYP2C19", phenotype_name=expected_phenotype)
    ]
    assert "CYP2C19:" in record.implication


def test_parse_recommendation_records_skips_rows_without_phenotypes_or_text():
    raw = [
        {"drugrecommendation": "Use standard dose", "phenotypes": {}},
        {"drugrecommendation": None, "phenotypes": {"CYP2C19": "Normal Metabolizer"}},
    ]

    assert parse_recommendation_records(raw, guideline_version=None) == []
