from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Gene(Base):
    __tablename__ = "genes"
    __table_args__ = {"schema": "knowledge"}

    gene_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    gene_symbol: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    gene_name: Mapped[str | None] = mapped_column(String(255))


class Drug(Base):
    __tablename__ = "drugs"
    __table_args__ = {"schema": "knowledge"}

    drug_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    generic_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    drug_class: Mapped[str | None] = mapped_column(String(255))


class Phenotype(Base):
    __tablename__ = "phenotypes"
    __table_args__ = {"schema": "knowledge"}

    phenotype_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phenotype_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    phenotype_description: Mapped[str | None] = mapped_column(Text)


class DrugGeneMapping(Base):
    __tablename__ = "drug_gene_mapping"
    __table_args__ = (UniqueConstraint("drug_id", "gene_id", name="uq_drug_gene"), {"schema": "knowledge"})

    mapping_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    drug_id: Mapped[int] = mapped_column(ForeignKey("knowledge.drugs.drug_id"), nullable=False)
    gene_id: Mapped[int] = mapped_column(ForeignKey("knowledge.genes.gene_id"), nullable=False)


class Allele(Base):
    __tablename__ = "alleles"
    __table_args__ = (UniqueConstraint("gene_id", "star_allele", name="uq_gene_allele"), {"schema": "knowledge"})

    allele_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    gene_id: Mapped[int] = mapped_column(ForeignKey("knowledge.genes.gene_id"), nullable=False)
    star_allele: Mapped[str] = mapped_column(String(20), nullable=False)
    functionality: Mapped[str | None] = mapped_column(String(100))
    activity_value: Mapped[float | None] = mapped_column(Numeric(5, 2))


class GenotypePhenotypeMapping(Base):
    __tablename__ = "genotype_phenotype_mapping"
    __table_args__ = {"schema": "knowledge"}

    mapping_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    gene_id: Mapped[int] = mapped_column(ForeignKey("knowledge.genes.gene_id"), nullable=False)
    allele1: Mapped[str] = mapped_column(String(20), nullable=False)
    allele2: Mapped[str] = mapped_column(String(20), nullable=False)
    activity_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    phenotype_id: Mapped[int | None] = mapped_column(
        ForeignKey("knowledge.phenotypes.phenotype_id")
    )


class PgxRecommendation(Base):
    __tablename__ = "pgx_recommendations"
    __table_args__ = {"schema": "knowledge"}

    recommendation_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    drug_id: Mapped[int] = mapped_column(ForeignKey("knowledge.drugs.drug_id"), nullable=False)
    recommendation_text: Mapped[str] = mapped_column(Text, nullable=False)
    implication: Mapped[str | None] = mapped_column(Text)
    recommendation_strength: Mapped[str | None] = mapped_column(String(50))
    classification: Mapped[str | None] = mapped_column(String(100))
    source: Mapped[str | None] = mapped_column(String(100))
    cpic_guideline_version: Mapped[str | None] = mapped_column(String(50))
    evidence_level: Mapped[str | None] = mapped_column(String(20))
    recommendation_order: Mapped[int | None] = mapped_column(Integer)


class PgxRecommendationGene(Base):
    __tablename__ = "pgx_recommendation_genes"
    __table_args__ = (
        UniqueConstraint("recommendation_id", "gene_id", name="uq_recommendation_gene"),
        {"schema": "knowledge"},
    )

    recommendation_gene_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recommendation_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge.pgx_recommendations.recommendation_id", ondelete="CASCADE"),
        nullable=False,
    )
    gene_id: Mapped[int] = mapped_column(ForeignKey("knowledge.genes.gene_id"), nullable=False)


class PgxRecommendationPhenotype(Base):
    __tablename__ = "pgx_recommendation_phenotypes"
    __table_args__ = (
        UniqueConstraint("recommendation_id", "gene_id", "phenotype_id", name="uq_rec_gene_pheno"),
        {"schema": "knowledge"},
    )

    recommendation_phenotype_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recommendation_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge.pgx_recommendations.recommendation_id", ondelete="CASCADE"),
        nullable=False,
    )
    gene_id: Mapped[int] = mapped_column(ForeignKey("knowledge.genes.gene_id"), nullable=False)
    phenotype_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge.phenotypes.phenotype_id"), nullable=False
    )

