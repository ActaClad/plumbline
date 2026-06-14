"""An eval script using a dedicated LLM-eval framework — counts as a suite."""
import deepeval
from deepeval.metrics import AnswerRelevancyMetric

from agent import summarize


def run_eval(dataset):
    metric = AnswerRelevancyMetric(threshold=0.7)
    for case in dataset:
        deepeval.assert_test(summarize(case.input), [metric])
