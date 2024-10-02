from random import choice, randint, randrange

VARIABLE_LIST = ['x', 'y', 'z', 't', 'm']
FRUIT_NAME_LIST = [['яблоко', 'яблока', 'яблок'],
                   ['груша', 'груши', 'груш'],
                   ['апельсин', 'апельсина', 'апельсинов'],
                   ['слива', 'сливы', 'слив'],
                   ['персик', 'персика', 'персиков']]
MEAS_UNITS = ['см', 'м', 'дм']


class Tasks:
    def __init__(self):
        self.question = ''
        self.answer = 0
        self.name = ''

    def scales_and_fruis(self):

        self.name = 'scales_and_fruis'
        self.answer = randrange(50, 120, 1)
        a = randrange(1, 10, 1)
        b = randrange(0, 1000, 10)
        multiply = a * self.answer
        c = multiply + b

        fruit = randrange(0, len(FRUIT_NAME_LIST), 1)
        if a == 1:
            variable = FRUIT_NAME_LIST[fruit][0]
        elif a in range(2, 5):
            variable = FRUIT_NAME_LIST[fruit][1]
        else:
            variable = FRUIT_NAME_LIST[fruit][2]

        if fruit in [0, 2, 4]:
            odin_word = f'одного {FRUIT_NAME_LIST[fruit][1]}'
        elif fruit == 1:
            odin_word = f'одной {FRUIT_NAME_LIST[fruit][1]}'
        else:
            odin_word = f'одной {FRUIT_NAME_LIST[fruit][1]}'

        self.question = (f'На весах с одной стороны лежит {a} '
                         f'{variable} и гири общей массой  {b} '
                         f'грамм.\nА на другой чаше весов лежат гири массой '
                         f'{c} грамм. \nКакова масса {odin_word}?\n')

    def fruit_picking(self,):

        self.name = 'fruit_picking'
        x = randint(3, 100)
        a = randint(2, 15)
        less_or_more_index = randint(0, 2)
        self.answer = x + a * x

        fruit = choice(FRUIT_NAME_LIST)[2]

        if less_or_more_index == 0:
            less_more = "меньше"
            less_more1 = "больше"
        else:
            less_more = "больше"
            less_more1 = "меньше"

        self.question = (f'Во второй день собрали в {a} раз {less_more} '
                         f'{fruit} чем в первый.\nПри этом оказалось, что '
                         f'в первый день собрали на {self.answer - (2 * x)} '
                         f'{less_more1} {fruit} чем во второй.\nСколько '
                         f'{fruit} собрали за оба дня?\n')

    def linear_equasion(self):

        self.name = 'linear_equasion'
        variable = choice(VARIABLE_LIST)
        self.answer = randint(3, 99)
        a = randint(2, 9)
        b = randint(1, a*self.answer)
        sign = choice(['+', '++', '-'])
        if sign == '-':
            c = a * self.answer - b
        else:
            c = a * self.answer + b

        if sign == '+':
            string = f'{a} * {variable} + {b} = {c}'
        elif sign == '++':
            string = f'{b} + {a} * {variable} = {c}'
        else:
            string = f'{a} * {variable} - {b} = {c}'

        self.question = f'{string}\nЧему равно {variable}?\n'

    def area_and_perimeter(self):

        self.name = 'area_and_perimeter'
        meas_units = choice(MEAS_UNITS)
        sqare_side = choice([4, 6, 8, 9, 10, 12, 14, 15, 16, 18,
                            20, 21, 22, 24, 25, 26, 27, 28, 30])
        area = sqare_side**2
        divisors = []
        for i in range(2, area):
            if area % i == 0:
                divisors.append(i)
        divisors.remove(sqare_side)
        rect_side_1 = choice(divisors)
        rect_side_2 = int(area/rect_side_1)
        self.answer = (rect_side_1*2 + rect_side_2*2)
        self.question = (f'Даны прямоугольник и квадрат с одинаковой площадью.\n'
                         f'Известно, что одна сторона прямоугольника {rect_side_1} {meas_units}, '
                         f'а сторона квадрата {sqare_side} {meas_units}\n'
                         f'Найдите периметр прямоугольника.\n')

    def random_task(self):
        random_func = choice(
            [self.scales_and_fruis,
             self.fruit_picking,
             self.linear_equasion,
             self.area_and_perimeter]
        )
        random_func()
