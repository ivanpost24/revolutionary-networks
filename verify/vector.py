import re
import sys
from collections.abc import Iterable
from itertools import pairwise

import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline

from revnet_verify.rotunda import get_revnet_data

NONTOKEN_PATTERN = re.compile(r'[^\w ]|[0-9]', flags=re.IGNORECASE)


def digraph_analyzer(text: str) -> Iterable[str]:
    ngrams = NONTOKEN_PATTERN.sub('', text.casefold()).split(' ')
    return (''.join(pair) for ngram in ngrams for pair in pairwise(ngram))


def get_pipeline() -> Pipeline:
    return Pipeline([
        ('digraph', TfidfVectorizer(analyzer=digraph_analyzer, sublinear_tf=True)),
        ('lsa', TruncatedSVD(n_components=200)),
        ('knn', KNeighborsClassifier(n_neighbors=5, weights='distance', metric='cosine')),
    ])


def compute_cross_val_score() -> None:
    data = (
        pd.read_csv('../rotunda_data_1771-1783_full.csv')
        .dropna(how='any', subset=['OrigDateline', 'Location'])
        .set_index('DocumentID')
    )
    model = get_pipeline()
    print('cross-validated mean accuracy:', cross_val_score(model, data['OrigDateline'], data['Location']).mean())


def infer_locations_during_revolutionary_period() -> None:
    data = (
        pd.read_csv('../rotunda_data_1771-1783_full.csv')
        .dropna(how='any', subset=['OrigDateline', 'Location'])
        .set_index('DocumentID')
    )
    model = get_pipeline()
    X_train, X_test, y_train, y_test = train_test_split(data['OrigDateline'], data['Location'], test_size=0.2)
    model.fit(X_train, y_train)

    estimates = pd.DataFrame(
        model.predict_proba(data['OrigDateline']),
        index=data.index,
        columns=model.classes_
    )
    top2 = estimates.apply(lambda row: row.nlargest(2).values, axis='columns', result_type='expand')
    confusion = (top2.loc[:, 1] / top2.loc[:, 0]).rename('Confusion')

    result = (
        data
        .join(pd.DataFrame(estimates.idxmax(axis='columns').rename('InferredLocation')), how='left')
        .join(pd.DataFrame(estimates.max(axis='columns').rename('LocationProba')), how='left')
        .join(pd.DataFrame(confusion), how='left')
    )
    result['InTestSet'] = False
    result.loc[X_test.index, 'InTestSet'] = True
    result.to_csv('../rotunda_data_1771-1783_full_inferred.csv')

    print('accuracy:', model.score(X_test, y_test))


def infer_missing_locations() -> None:
    data = get_revnet_data('../rotunda_data_1771-1783_full.csv').set_index('DocumentID')
    train_data = (
        data
        .dropna(how='any', subset=['OrigDateline', 'Location'])
    )
    model = get_pipeline()
    model.fit(train_data['OrigDateline'], train_data['Location'])
    test_data = (
        data[pd.isna(data['Location']) & pd.notna(data['OrigDateline'])]
    )

    estimates = pd.DataFrame(
        model.predict_proba(test_data['OrigDateline']),
        index=test_data.index,
        columns=model.classes_
    )
    top2 = estimates.apply(lambda row: row.nlargest(2).values, axis='columns', result_type='expand')
    confusion = (top2.loc[:, 1] / top2.loc[:, 0]).rename('Confusion')

    result = (
        test_data
        .join(pd.DataFrame(estimates.idxmax(axis='columns').rename('InferredLocation')), how='left')
        .join(pd.DataFrame(estimates.max(axis='columns').rename('LocationProba')), how='left')
        .join(pd.DataFrame(confusion), how='left')
    )
    result.to_csv('/Users/ivan/Downloads/rotunda_data_1771-1783_filled.csv')


def infer_new_locations() -> None:
    train_data = (
        get_revnet_data('../rotunda_data_1771-1783_full.csv')
        .dropna(how='any', subset=['OrigDateline', 'Location'])
        .set_index('DocumentID')
    )
    model = get_pipeline()
    model.fit(train_data['OrigDateline'], train_data['Location'])
    test_data = (
        pd.read_csv(sys.argv[1])
        .dropna(how='any', subset=['OrigDateline'])
        .set_index('DocumentID')
    )

    estimates = pd.DataFrame(
        model.predict_proba(test_data['OrigDateline']),
        index=test_data.index,
        columns=model.classes_
    )
    top2 = estimates.apply(lambda row: row.nlargest(2).values, axis='columns', result_type='expand')
    confusion = (top2.loc[:, 1] / top2.loc[:, 0]).rename('Confusion')

    result = (
        test_data
        .join(pd.DataFrame(estimates.idxmax(axis='columns').rename('InferredLocation')), how='left')
        .join(pd.DataFrame(estimates.max(axis='columns').rename('LocationProba')), how='left')
        .join(pd.DataFrame(confusion), how='left')
    )
    result.to_csv('locations_inferred.csv')


if __name__ == '__main__':
    infer_new_locations()
