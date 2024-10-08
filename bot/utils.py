from datetime import date


def str_date(date: date):
    months = {'01': 'января',
              '02': 'февраля',
              '03': 'марта',
              '04': 'апреля',
              '05': 'мая',
              '06': 'июня',
              '07': 'июля',
              '08': 'августа',
              '09': 'сентября',
              '10': 'октября',
              '11': 'ноября',
              '12': 'декабря'}
    day = date.strftime('%#d')
    month = months[date.strftime('%m')]
    return f'{day} {month}'
