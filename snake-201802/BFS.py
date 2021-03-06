import bottle
import os
import random
from random import randint
from math import *
from copy import copy, deepcopy


ENEMY = 1
WALL = 2
SAFE = 5
#------------------------------------------------------------------------------------------------------------
game_id = ''
board_width = 0
board_height = 0
board = None
#------------------------------------------------------------------------------------------------------------

@bottle.route('/')
def static():
    return "the server is running"


@bottle.route('/static/<path:path>')
def static(path):
    return bottle.static_file(path, root='static/')


@bottle.post('/start')
def start():
    data = bottle.request.json
    global game_id
    global board_width
    global board_height
    game_id = data.get('game_id')
    board_width = data.get('width')
    board_height = data.get('height')

    head_url = '%s://%s/static/head2.png' % (
        bottle.request.urlparts.scheme,
        bottle.request.urlparts.netloc
    )

    # TODO: Do things with data
    return {
        'color': '#E74C3C',
        'taunt': '{} ({}x{})'.format(game_id, board_width, board_height),
        'head_url': head_url,
        'name': 'cc',
        "head_type": "tongue",
        "tail_type": "pixel"
    }
                            

#------------------------------------------------------------------------------------------------------------
@bottle.post('/move')
def move():
    data = bottle.request.json

    #crate a 2d array for board: all values are 0
    global board
    board = [[0 for x in range(board_width)] for y in range(board_height)] 

    #get food location
    my_food_list = []
    food_list = data.get('food')['data']
    for each_food in food_list:
        food_x = each_food['y']
        food_y = each_food['x']
        my_food_list.append([food_x, food_y]) #my_food_list e.g. [[12,1], [23,12], [0,9]]

    #get the location of myself
    my_body_list = []
    body_list = data.get('you')['body']['data']
    my_len = data.get('you')['length']
    my_id = data.get('you')['id']
    for each_segment in body_list:
        segment_x = each_segment['y']
        segment_y = each_segment['x']
        my_body_list.append([segment_x,segment_y]) #my_body_list e.g. [[1,1], [2,1], [2,2], 3] #first coor is the head!!
    my_body_list.append(my_len)

    #get the location of other snakes   (TODO!!!)
    enemy_body_list = []
    enemy_list = data.get('snakes')['data']
    for each_enemy in enemy_list:
        each_enemy_snake = []
        each_enemy_len = each_enemy['length']
        each_enemy_health = each_enemy['health']
           
        if (each_enemy['id'] != my_id) and (each_enemy_health != 0):
            for each_enemy_segement in each_enemy['body']['data']:
                enemy_body_x = each_enemy_segement['y']
                enemy_body_y = each_enemy_segement['x']
                each_enemy_snake.append([enemy_body_x, enemy_body_y])
            each_enemy_snake.append(each_enemy_len)  
            enemy_body_list.append(each_enemy_snake)   #enemy_body_list e.g [ [[2,3],[2,4],2], [[5,6],[5,7],[5,8],3] ]  two snakes
    # print(enemy_body_list)


    #set danger zone
    board = set_walls(my_food_list, my_body_list, enemy_body_list)

    #get the position of the snake head
    head = my_body_list[0] #e.g.[1,1]

    #get the optional directions for the head (avoid walls and danger zone)
    directions = direction_options(head)
    
    #find the direction towards the closest food)
    direction = find_best_direction(directions, head, my_food_list, my_body_list)

    for i in board:
        print ("board:", i)
    return {
        'move': direction,
        'taunt': 'I\'m drunk'
    } 


#set danger zones in the board
def set_walls(my_food_list,my_body_list, enemy_body_list):
    global board
    # 1. set all snakes' position as danger zone
    for each_segment in my_body_list[0:len(my_body_list)-1:1]:  #[1,1]
        board[each_segment[0]][each_segment[1]] = 1
        
    for each_snake in enemy_body_list:
        for each_segment in each_snake[0:len(each_snake)-1:1]:
            board[each_segment[0]][each_segment[1]] = 1
    
    # 2. reopen some tail position
    reopen = get_open_coordinates(my_food_list, my_body_list, enemy_body_list) #e.g.[[2,3], [4,5]]
    for each_coor in reopen:
        board[each_coor[0]][each_coor[1]] = 0

    # 3. set longer snakes' next steps as danger zone
    for each_enemy in enemy_body_list:
        if each_enemy[-1] >= my_body_list[-1]:
            enemy_head = each_enemy[0]
            head_next_location = next_move_location(enemy_head)
            for next in head_next_location:
                board[next[0]][next[1]] = 1

    return board

#get the coordination of next move
def next_move_location(current_location):
    global board
    next_location = []
    directions = direction_options(current_location)
    for next_move in directions:
        if next_move == 'up':
            next_location.append([current_location[0]-1,current_location[1]])
        elif next_move == 'down':
            next_location.append([current_location[0]+1,current_location[1]])
        elif next_move == 'left':
            next_location.append([current_location[0],current_location[1]-1])
        elif next_move == 'right':
            next_location.append([current_location[0],current_location[1]+1])
    return next_location
    

#get the direction options of my snake head (avoid walls and danger zone)
def direction_options(head):#[3,6]
    global board
    global board_width
    global board_height
    curx = head[1]#6
    cury = head[0]#3
    directions = []
    #check if we can move up
    if cury >= 1:
        if board[cury-1][curx] == 0:#[2,6]
             directions.append('up')
    #check if we can move right
    if curx <= board_width - 2:
        if board[cury][curx+1] == 0:#[3,7]
             directions.append('right')
    #check if we can move left
    if curx >= 1:
        if board[cury][curx-1] == 0:#[3,5]
             directions.append('left')
    #check if we can move down
    if cury <= board_height - 2:#[4,6]
        if board[cury+1][curx] == 0:
             directions.append('down')
    return directions

#calculate the direction towards the closest food
def find_best_direction(directions, head, my_food_list, my_body_list):
    direction = ''
    #chase the losest food
    food_pos = my_food_list[0]
    min_distance_food = get_distance(head[1], head[0], my_food_list[0][1], my_food_list[0][0])
    for i in my_food_list:
        distance_food = get_distance(head[1], head[0], i[1], i[0])
        if distance_food <= min_distance_food:
            food_pos = i
            min_distance_food = distance_food

    global board
    global board_width
    global board_height
    grid = {}
    for y in range(0,board_height):
        for x in range(0,board_width):
            neighbor_list = next_move_location([y,x])
            str_list = []
            each_cell = pos_to_string([y,x])
            for i in neighbor_list:
                str_list.append(pos_to_string(i))
            grid[each_cell] = str_list

    path_str =  bfs(grid, pos_to_string(head), pos_to_string(food_pos))
    path_pos = [] #shortest path
    for i in path_str:
        path_pos.append(string_to_pos(i))

    print(path_pos)
    first_pos = path_pos[1]
    if first_pos[0] == head[0]:
        if first_pos[1] > head[1]:
            return 'right'
        else:
            return 'left'
    elif first_pos[0] > head[0]:
        return 'down'
    else:
        return 'up'

#When snakes move 1 step, their tail positons will be open again, (unless get a food)
def get_open_coordinates(my_food_list, my_body_list, enemy_body_list):
    open_coor =[]
    if my_body_list[-2] != my_body_list[-3]:
        my_next_locations = next_move_location(my_body_list[0])
        common = 0
        for i in my_next_locations:
            if i in my_food_list: 
                common += 1
        if common == 0:
            open_coor.append(my_body_list[-2])

    for enemy_snake in enemy_body_list:
        if enemy_snake[-2] != enemy_snake[-3]: #last two elements not the same
            enemy_next_locations = next_move_location(enemy_snake[0])
            common = 0
            for i in enemy_next_locations:
                if i in my_food_list:
                    common += 1
            if common == 0:
                open_coor.append(enemy_snake[-2])
    return open_coor

def get_distance(x1, y1, x2, y2):
    distance = ((x1-x2)**2)+((y1-y2)**2)
    return distance


#--------------------------------------------------------------------------------------------------------------

def bfs(grid, start, end):
    queue = []
    queue.append([start])
    while queue:
        path = queue.pop(0)
        node = path[-1]
        if node == end:
            return path
        for adjacent in grid.get(node, []):
            new_path = list(path)
            new_path.append(adjacent)
            queue.append(new_path)



#[2,3] to '2,3'
def pos_to_string(pos):
    return str(str(pos[0])+','+str(pos[1]))

def string_to_pos(string):
    return [int(string[0:1]), int(string[2:3])]
#------------------------------------------------------------------------------------------------------------
@bottle.post('/end')
def end():
    data = bottle.request.json
    return {'taunt': 'uh'}


# Expose WSGI app (so gunicorn can find it)
application = bottle.default_app()

if __name__ == '__main__':
    bottle.run(
        application,
        host=os.getenv('IP', '0.0.0.0'),
        port=os.getenv('PORT', '7070'),
        debug = True)