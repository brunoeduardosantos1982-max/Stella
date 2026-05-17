"""Camada de revisao de qualidade — Stella supervisora dos agentes.

ReviewPolicy decide QUANDO revisar (Q1=C do Design).
QualityReviewer aplica revisao via LLM (Q2=E — loop retry).
FeedbackLogger acumula correcoes do Bruno (Q3=C — aprende).
"""
