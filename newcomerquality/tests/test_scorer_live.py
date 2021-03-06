from newcomerquality.scorer import score_newcomer_first_days
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s:%(name)s -- %(message)s',
    filename='logs/newcomer_prediction.log', filemode='w',
)
logg = logging.getLogger()

def test_scorer_live(test_user_ids):
    '''needs an active connection'''
    for test_user_id in test_user_ids:
        user_score_ret = score_newcomer_first_days(test_user_id)
        print('predict user runtime took {t1-t0}')
        if user_score_ret['error']:
            logg.info(f'For some reason could not get contrib data for user {test_user_id}')
        elif not user_score_ret['error']:
            logg.info(f"User score for user {test_user_id} is {user_score_ret['user_id']}")
            print(user_score_ret['newcomer_predictions']['sessions_goodfaith_proba_min'])

if __name__ == '__main__':
    test_scorer_live()
