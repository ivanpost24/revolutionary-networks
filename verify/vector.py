import re
from collections.abc import Iterable
from itertools import pairwise

import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline


NONTOKEN_PATTERN = re.compile(r'[^\w ]|[0-9]', flags=re.IGNORECASE)


def digraph_analyzer(text: str) -> Iterable[str]:
    ngrams = NONTOKEN_PATTERN.sub('', text.casefold()).split(' ')
    return (''.join(pair) for ngram in ngrams for pair in pairwise(ngram))


def get_pipeline() -> Pipeline:
    return Pipeline([
        ('digraph', TfidfVectorizer(analyzer=digraph_analyzer, sublinear_tf=True)),
        ('lsa', TruncatedSVD(n_components=100)),
        ('knn', KNeighborsClassifier(n_neighbors=5, weights='distance', metric='cosine')),
    ])


def find_best_model(X_train: pd.Series[str], y_train: pd.Series[str]) -> GridSearchCV:
    searcher = GridSearchCV(
        get_pipeline(),
        param_grid={
            'lsa__n_components': [2, 5, 10, 25, 50, 75, 100],
            'knn__n_neighbors': [5, 10, 25, 50, 75, 100],
            'knn__weights': ['uniform', 'distance'],
        },
        scoring='accuracy',
        n_jobs=-1,
    )
    searcher.fit(X_train, y_train)
    return searcher


def main() -> None:
    data = (
        pd.read_csv('../rotunda_data_1771-1783_full.csv')
        .dropna(how='any', subset=['OrigDateline', 'Location'])
        .set_index('DocumentID')
    )
    X_train, X_test, y_train, y_test = train_test_split(data['OrigDateline'], data['Location'], test_size=0.2)
    location_classifier = get_pipeline()
    location_classifier.fit(X_train, y_train)
    print('accuracy:', location_classifier.score(X_test, y_test))

    estimates = pd.DataFrame(
        location_classifier.predict_proba(data['OrigDateline']),
        index=data.index,
        columns=location_classifier.classes_
    )
    result = (
        data
        .join(pd.DataFrame(estimates.idxmax(axis='columns').rename('InferredLocation')), how='left')
        .join(pd.DataFrame(estimates.max(axis='columns').rename('LocationProba')), how='left')
    )
    result.to_csv('inferred_locations.csv')


if __name__ == '__main__':
    main()
