"""Small deterministic model used by AI267 practice Task 08."""

from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression


def train_model() -> LogisticRegression:
    features, labels = make_classification(
        n_samples=200,
        n_features=8,
        n_informative=5,
        random_state=267,
    )
    model = LogisticRegression(max_iter=500, random_state=267)
    model.fit(features, labels)
    return model


# ``%run /opt/app-root/src/train_carido_model.py`` exposes this trained model
# in the notebook namespace. Saving it is intentionally the learner's task.
ml_model = train_model()
