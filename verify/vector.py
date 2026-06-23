import re
from collections import Counter
from collections.abc import Iterable, Collection, Mapping
from itertools import pairwise

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import sklearn as sk
from sklearn.decomposition import PCA, TruncatedSVD
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import train_test_split

from revnet_verify.rotunda import get_revnet_data

NONTOKEN_PATTERN = re.compile(r'[^\w ]|[0-9]', flags=re.IGNORECASE)


def count_digraphs(text: str, digraphs: Collection[str] | None = None) -> Mapping[str, int]:
    ngrams = NONTOKEN_PATTERN.sub('', text.casefold()).split(' ')
    digraph_gen = (''.join(pair) for ngram in ngrams for pair in pairwise(ngram))
    if digraphs is not None:
        counts = dict.fromkeys(digraphs, 0)
        for digraph in digraph_gen:
            if digraph in counts:
                counts[digraph] += 1
        return counts
    else:
        return Counter(digraph_gen)


class DigraphReducer:
    def __init__(self, **kwargs):
        self.__pca = TruncatedSVD(**kwargs)
        self.__pca.set_output(transform='pandas')
        self.__digraphs = None

    def fit_transform(self, data: pd.DataFrame) -> pd.DataFrame:
        digraph_vectors = self.__get_digraph_vectors(data)
        self.__digraphs = digraph_vectors.columns
        return self.__pca.fit_transform(digraph_vectors)

    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        if self.__digraphs is None:
            raise RuntimeError('DigraphReducer is not fitted yet')
        return self.__pca.transform(self.__get_digraph_vectors(data, digraphs=self.__digraphs))

    @staticmethod
    def __get_digraph_vectors(data: pd.DataFrame, digraphs: Collection[str] | None = None) -> pd.DataFrame:
        counts = pd.DataFrame(
            (count_digraphs(text, digraphs=digraphs) for text in data['OrigDateline']),
            index=data.index,
        ).fillna(0)
        counts = counts.loc[counts.sum(axis='columns') > 0, :]
        data = data.loc[counts.index, :]

        with np.errstate(divide='ignore'):
            # noinspection PyTypeChecker
            tf: pd.DataFrame = 1 + np.log(counts)
        tf[(tf < 0) | np.isinf(tf)] = 0
        df = counts[counts > 0].sum(axis='index')
        with np.errstate(divide='ignore'):
            idf = 1 + np.log(len(data)) - np.log(df)
        idf[(idf < 0) | np.isinf(idf)] = 0
        measure = tf.mul(idf, axis='columns')
        return measure.div(np.sqrt((measure * measure).sum(axis='columns')), axis='index')


def encode_digraphs(
        data: pd.DataFrame,
        transformer: sk.base.TransformerMixin,
        fit: bool,
        use_tf_idf: bool = True
) -> pd.DataFrame:
    counts = pd.DataFrame(
        (count_digraphs(text) for text in data['OrigDateline']),
        index=data.index,
    ).fillna(0)
    counts = counts.loc[counts.sum(axis='columns') > 0, :]
    data = data.loc[counts.index, :]

    if use_tf_idf:
        with np.errstate(divide='ignore'):
            # noinspection PyTypeChecker
            tf: pd.DataFrame = 1 + np.log(counts)
        tf[tf < 0] = 0
        df = counts[counts > 0].sum(axis='index')
        idf = 1 + np.log(len(data)) - np.log(df)
        measure = tf.mul(idf, axis='columns')
        measure = measure.div(np.sqrt((measure * measure).sum(axis='columns')), axis='index')
    else:
        measure = counts.div(counts.sum(axis='columns'), axis='index')

    if hasattr(transformer, 'transform') and not fit:
        return transformer.transform(X=measure)
    else:
        return transformer.fit_transform(X=measure, y=data['Location'])


def encode_location(train_data: pd.DataFrame) -> pd.DataFrame:
    phi = np.radians(train_data['latitude'])
    theta = np.radians(train_data['longitude'])

    result = pd.DataFrame(np.nan, index=train_data.index, columns=['geo0', 'geo1', 'geo2'], dtype=np.float64)
    result['geo0'] = np.cos(phi) * np.cos(theta)
    result['geo1'] = np.cos(phi) * np.sin(theta)
    result['geo2'] = np.sin(phi)

    return result


def encode_date(train_data: pd.DataFrame) -> pd.DataFrame:
    date = (train_data['Date'] - train_data['Date'].min()).dt.total_seconds()
    date *= np.pi / 2 / date.max()

    result = pd.DataFrame(np.nan, index=train_data.index, columns=['date0', 'date1'], dtype=np.float64)
    result['date0'] = np.cos(date)
    result['date1'] = np.sin(date)

    return result


def trial_dimensionality_reductions(
        train_data: pd.DataFrame,
        transformers: Iterable[tuple[sk.base.TransformerMixin, str, bool]]
) -> None:
    for transformer, name, use_tf_idf in transformers:
        embeddings = encode_digraphs(train_data, transformer, use_tf_idf=use_tf_idf)
        result = pd.concat(
            [
                train_data,
                embeddings
            ],
            axis='columns',
            verify_integrity=True
        )
        fig, ax = plt.subplots(figsize=(10, 10))
        sns.scatterplot(result, x='digraph0', y='digraph1', hue='Location', ax=ax)
        ax.set_title(f'{name} [{transformer}]')
        plt.show()


def main() -> None:
    data = get_revnet_data('../rotunda_data_1771-1783_full.csv')
    data = data.loc[
        (
            (data['OrigDateline'].str.len() > 0)
            & data['Location'].isin(data['Location'].value_counts().index[:10])
            & pd.notna(data['Location'])
        ),
        ['DocumentID', 'OrigDateline', 'Location']
    ].set_index('DocumentID')
    train_data, test_data = train_test_split(data.head(1000), test_size=0.2)
    digraph_reducer = DigraphReducer(n_components=100)
    train_embedding = digraph_reducer.fit_transform(train_data)
    test_embedding = digraph_reducer.transform(test_data)
    similarity_matrix = pd.DataFrame(
        cosine_similarity(test_embedding, train_embedding),
        index=test_embedding.index,
        columns=train_embedding.index
    )
    neighbors: pd.DataFrame = similarity_matrix.apply(  # type: ignore
        lambda row: train_data.loc[row.nlargest(25).index, 'Location'].values,
        axis='columns',
        result_type='expand',
    )
    best_matches = pd.DataFrame(neighbors.mode(axis='columns')[0].rename('InferredLocation'))
    result = test_data[pd.notna(test_data['Location'])].join(best_matches, how='left')
    print('accuracy:', (result['Location'] == result['InferredLocation']).sum() / len(test_data))
    result.to_csv('inferred_locations.csv')


if __name__ == '__main__':
    main()
