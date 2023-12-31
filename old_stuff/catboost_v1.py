import pandas as pd
import numpy as np
from catboost import CatBoostRegressor, Pool
from sklearn.model_selection import train_test_split
import gc
import matplotlib.pyplot as plt


print('Loading Properties...')
properties2016 = pd.read_csv('data/properties_2016.csv', low_memory = False)
properties2017 = pd.read_csv('data/properties_2017.csv', low_memory = False)

print('Loading Train...')
train2016 = pd.read_csv('data/train_2016_v2.csv', parse_dates=['transactiondate'], low_memory=False)
train2017 = pd.read_csv('data/train_2017.csv', parse_dates=['transactiondate'], low_memory=False)

print('Loading Sample ...')
sample_submission = pd.read_csv('data/sample_submission.csv', low_memory=False)

def add_date_features(df):
    df["transaction_year"] = df["transactiondate"].dt.year
    df["transaction_month"] = df["transactiondate"].dt.month
    df["transaction_day"] = df["transactiondate"].dt.day
    df["transaction_quarter"] = df["transactiondate"].dt.quarter
    df.drop(["transactiondate"], inplace=True, axis=1)
    return df

train2016 = add_date_features(train2016)
train2017 = add_date_features(train2017)

sample_submission['parcelid'] = sample_submission['ParcelId']

print('Merge Train & Test with Properties...')
train2016 = pd.merge(train2016, properties2016, how='left', on='parcelid')
train2017 = pd.merge(train2017, properties2017, how='left', on='parcelid')
test_df = pd.merge(sample_submission, properties2016, how='left', on='parcelid')

print('Concat Train 2016 & 2017...')
train_df = pd.concat([train2016, train2017], axis=0)

del properties2016, properties2017, train2016, train2017
gc.collect();

print("Train: ", train_df.shape)
print("Test: ", test_df.shape)


missing_perc_thresh = 0.98
exclude_missing = []
num_rows = train_df.shape[0]
for c in train_df.columns:
    num_missing = train_df[c].isnull().sum()
    if num_missing == 0:
        continue
    missing_frac = num_missing / float(num_rows)
    if missing_frac > missing_perc_thresh:
        exclude_missing.append(c)
print("We exclude: %s" % exclude_missing)
print(len(exclude_missing))


exclude_unique = []
for c in train_df.columns:
    num_uniques = len(train_df[c].unique())
    if train_df[c].isnull().sum() != 0:
        num_uniques -= 1
    if num_uniques == 1:
        exclude_unique.append(c)
print("We exclude: %s" % exclude_unique)
print(len(exclude_unique))

exclude_other = ['parcelid', 'logerror','propertyzoningdesc']
train_features = []
for c in train_df.columns:
    if c not in exclude_missing \
       and c not in exclude_other and c not in exclude_unique:
        train_features.append(c)
print("We use these for training: %s" % train_features)
print(len(train_features))


cat_feature_inds = []
cat_unique_thresh = 1000
for i, c in enumerate(train_features):
    num_uniques = len(train_df[c].unique())
    if num_uniques < cat_unique_thresh \
       and not 'sqft' in c \
       and not 'cnt' in c \
       and not 'nbr' in c \
       and not 'number' in c:
        cat_feature_inds.append(i)
        
print("Cat features are: %s" % [train_features[ind] for ind in cat_feature_inds])


print ("Replacing NaN values by -999 !!")
train_df.fillna(-999, inplace=True)
test_df.fillna(-999, inplace=True)

def print_feature_importance(model, pool, X_train):
    feature_importances = model.get_feature_importance(pool)
    feature_names = X_train.columns
    for score, name in sorted(zip(feature_importances, feature_names), reverse=True):
        print('{}\t{}'.format(name, score))

feature_list = [train_features[ind] for ind in cat_feature_inds]

for col in train_df[train_features]:
    if col in feature_list:
        train_df[col] = train_df[col].astype(str)


X_train, X_test, y_train, y_test = train_test_split(train_df[train_features], train_df.logerror, test_size=0.2, random_state=99)
print(X_train.shape, y_train.shape)
print(X_test.shape, y_test.shape)


all_pool = Pool(train_df[train_features], train_df.logerror, cat_feature_inds)
train_pool = Pool(X_train, y_train, cat_feature_inds)
test_pool = Pool(X_test, y_test, cat_feature_inds)

catboost_parameters = {
    'iterations': 400,
    'learning_rate': 0.035,
    'depth': 7,
    'verbose': 20,
#     'l2_leaf_reg': 1000,
    'task_type': 'CPU',
    'loss_function': 'MAE',
    'eval_metric': 'MAE',
    'random_seed': 0,
}

model = CatBoostRegressor(**catboost_parameters)
model.fit(train_pool, eval_set=test_pool)

print_feature_importance(model, train_pool, X_train)


num_ensembles = 5
# ensemble models
models = [None] * num_ensembles
for i in range(num_ensembles):
    print("\nTraining (ensemble): %d ..." % (i))
    catboost_parameters['random_seed'] = i
    models[i] = CatBoostRegressor(**catboost_parameters)
    models[i].fit(train_pool, eval_set=test_pool)
    print('-- Feature Importance --')
    print_feature_importance(models[i], train_pool, X_train)


submission = pd.DataFrame({
    'ParcelId': test_df['parcelid'],
})

test_dates = {
    '201610': pd.Timestamp('2016-09-30'),
    '201611': pd.Timestamp('2016-10-31'),
    '201612': pd.Timestamp('2016-11-30'),
    '201710': pd.Timestamp('2017-09-30'),
    '201711': pd.Timestamp('2017-10-31'),
    '201712': pd.Timestamp('2017-11-30')
}

for label, test_date in test_dates.items():
    print("Predicting for: %s ... " % (label))
    test_df['transactiondate'] = test_date
    test_df = add_date_features(test_df)
    for col in test_df[train_features]:
        if col in feature_list:
            test_df[col] = test_df[col].astype(str)
    y_pred = 0.0
    for i in range(num_ensembles):
        print("Ensemble:", i)
        y_pred += models[i].predict(test_df[train_features])
    y_pred /= num_ensembles
    submission[label] = y_pred

submission_major = 2
print("Creating submission: submission_%03d.csv ..." % (submission_major))
submission.to_csv(
    'submission_%03d.csv' % (submission_major),
    float_format='%.4f',
    index=False)
print("Finished.")