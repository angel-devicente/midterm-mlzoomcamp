#!/usr/bin/env python
# coding: utf-8

import numpy as np
import pandas as pd
from datetime import datetime

from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

import bentoml 

#############  Functions

"""
Given ratings RA and RB, returns EA and EB 
  (expected probability of winning of player A and B, respectively) 
"""
def expected(ra,rb):
    ea = 1 / (1 + 10**((rb-ra)/400))
    eb = 1 / (1 + 10**((ra-rb)/400))
    return (ea,eb)

"""
Input: 
  RA, RB: ratings for players
  SA, SB: score of players (0: lose, 1 win)
  K     : ELO constant (the bigger, the larger movement of scores for each game)
            10 was proposed originally by Elo, 24 is used nowadays
Output:
  RA_n, RB_n: the new ratings for both players
"""
def scores(ra,rb,sa,sb,k=24):
    (ea,eb) = expected(ra,rb)
    ra_n = ra + k * (sa - ea)
    rb_n = rb + k * (sb - eb)
    return (ra_n,rb_n)

"""
Given a player, return its index in the 'all_players' list
"""
def find_iloc(player):
    return np.where(all_players == player)[0][0]


"""
Calculate the ELO ratings throughout the period covered by the dataset
 for a given player.

Output: list of ELO ratings, ordered by age (first in the list is the oldest)
"""
def rating_progress(player):
    rating_player = np.full(df.age.shape[0],0)
    rating_player[0] = 1500
    ratings = np.full((len(all_players)),1500)

    for i in range(df.age.shape[0]):
        p1i = find_iloc(df.player1[i])
        p2i = find_iloc(df.player2[i])
        r1 = ratings[p1i]
        r2 = ratings[p2i]
        if df.points1[i] > df.points2[i]:
            s1 = 1 
            s2 = 0
        else:
            s1 = 0
            s2 = 1

        r1n,r2n = scores(r1,r2,s1,s2)
        ratings[p1i] = r1n
        ratings[p2i] = r2n        
        if df.player1[i] == player:
            rating_player[i] = r1n
        elif df.player2[i] == player:
            rating_player[i] = r2n
        else:
            if i > 0:
                rating_player[i] = rating_player[i-1]
    
    return rating_player

############################

# parameters
# ----------
n_estimators     = 100
max_depth        =   5
min_samples_leaf =  20 

# data preparation
# ----------------
df = pd.read_csv('BWF-Data/ws.csv')

# let's get rid of the 42 matches where one player retired
df = df[df.retired == False]
del df['retired']
df.reset_index(inplace=True,drop=True)

# Keeping only essential features
# ------------------------------
features = ['date', 'team_one_players', 'team_two_players',
       'team_one_total_points', 'team_two_total_points', 'winner']
df = df[features]
df.rename(columns={'team_one_players':'player1','team_two_players':'player2'},inplace=True)
df.rename(columns={'team_one_total_points':'points1','team_two_total_points':'points2'},inplace=True)

df.player1 = df.player1.str.lower().str.replace(' ','_')
df.player2 = df.player2.str.lower().str.replace(' ','_')

# Transforming "date" to "age"
# ---------------------------
date_format = "%d-%m-%Y"
a = datetime.strptime('01-01-2022', date_format)
df['age'] = [(a - datetime.strptime(date, date_format)).days for date in df.date]
del df['date']

p1 = df.player1.unique()
p2 = df.player2.unique()
all_players = np.unique(np.concatenate((p1,p2)))

# Adding "ELO" data
# -----------------
ratings = np.full((len(all_players)),1500)

for i in range(df.age.shape[0]):
    p1i = find_iloc(df.player1[i])
    p2i = find_iloc(df.player2[i])
    r1 = ratings[p1i]
    r2 = ratings[p2i]
    if df.points1[i] > df.points2[i]:
        s1 = 1 
        s2 = 0
    else:
        s1 = 0
        s2 = 1
        
    r1n,r2n = scores(r1,r2,s1,s2)
    ratings[p1i] = r1n
    ratings[p2i] = r2n        

elo1 = [0] * df.age.shape[0]
elo2 = [0] * df.age.shape[0]

for i in range(df.age.shape[0]):
    p1i = find_iloc(df.player1[i])
    p2i = find_iloc(df.player2[i])
    elo1[i] = ratings[p1i]
    elo2[i] = ratings[p2i]

df["elo1"] = elo1
df["elo2"] = elo2

# Adding ELO gradient 
# -------------------
ratings  = np.full((len(all_players)),1500.)
delta    = np.full((len(all_players)),0.)    
gradient = np.full((len(all_players)),0.)    
                                             
df["grad1"] = [0] * df.age.shape[0]
df["grad2"] = [0] * df.age.shape[0]

for i in range(df.age.shape[0]):
    p1i = find_iloc(df.player1[i])
    p2i = find_iloc(df.player2[i])
    r1 = ratings[p1i]
    r2 = ratings[p2i]
    if df.points1[i] > df.points2[i]:
        s1 = 1 
        s2 = 0
    else:
        s1 = 0
        s2 = 1
        
    r1n,r2n = scores(r1,r2,s1,s2)
    ratings[p1i] = r1n
    ratings[p2i] = r2n        

    if i > 0:
        gradient[p1i] = delta[p1i]
        gradient[p2i] = delta[p2i]
        df.grad1[i] = gradient[p1i] 
        df.grad2[i] = gradient[p2i] 
        
    delta[p1i] = r1n - r1
    delta[p2i] = r2n - r2

# Model training
# --------------
df_train_full, df_test = train_test_split(df, test_size=0.2, random_state=42)

y_train_full = df_train_full.winner.to_numpy()
y_test = df_test.winner.to_numpy()

del df_train_full['player1']
del df_test['player1']

del df_train_full['player2']
del df_test['player2']

del df_train_full['points1']
del df_test['points1']

del df_train_full['points2']
del df_test['points2']

del df_train_full['winner']
del df_test['winner']

X_train_full = df_train_full.to_numpy()
X_test  = df_test.to_numpy()

print(f"\n\nTraining the Random Forest Classifier with following parameters: \n\
estimatores={n_estimators} \n\
max_depth={max_depth} \n\
min_samples_leaf={min_samples_leaf}")

rf = RandomForestClassifier(n_estimators=110, max_depth=5, min_samples_leaf= 20, random_state=42)
rf.fit(X_train_full, y_train_full)
y_pred = rf.predict(X_test)
acc = accuracy_score(y_test, y_pred)

print('\nAccuracy score on final test data: -> %.3f' % (acc))

print('\nSaving model as a Bento')
bentoml.sklearn.save_model('badminton_prediction',rf)

