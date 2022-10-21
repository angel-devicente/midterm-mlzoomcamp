import numpy as np

import bentoml
from bentoml.io import JSON

badminton_runner = bentoml.sklearn.get("badminton_prediction:latest").to_runner()
svc = bentoml.Service("badminton", runners=[badminton_runner])

@svc.api(input=JSON(), output=JSON())
def classify(match):
    vector = np.array([[match['age'],
                        match['elo1'],
                        match['elo2'],
                        match['grad1'],
                        match['grad2']]])                                                
    prediction = badminton_runner.predict.run(vector)
    winner = prediction[0]

    if winner == 1:
        return {
            "winner": "Player 1"
        }
    elif winner == 2:
        return {
            "winner": "Player 2"
        }
    else:
        return {
            "winner": "ERROR"
        }
