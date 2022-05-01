#!/usr/bin/env python3

import pygame
import os
import sys
from math import *
from dataclasses import dataclass
from copy import deepcopy

from pygame.locals import *

def color(i):
	return (int(255 * (1 + cos(i)) * 0.5), int(255 * (1 + cos(2 * i)) * 0.5), int(255 * (1 + cos(4 * i)) * 0.5))

@dataclass
class Gift:
	id: int
	name: str
	score: int
	w: int
	x: int
	y: int


@dataclass
class State:
	cur_w: int
	carrots: int
	cur_t: int
	p: list
	v: list
	score: int
	delivery: list
	during_each_second: list
	base_moments: list
	error: str


# define a main function
def main():
	args = sys.argv
	if len(args) < 2:
		print("usage: ./game.py c")
		quit(0)
	filename = [x for x in os.listdir(".") if x.startswith(args[1].lower()) and x.endswith(".in.txt")][0]
	with open(filename) as f:
		tl, rad, acc_rgs_cnt, gifts_cnt = map(int, f.readline().split())
		ws = []
		max_acc = []
		for i in range(acc_rgs_cnt):
			x, y = map(int, f.readline().split())
			ws.append(x)
			max_acc.append(y)
		max_acc.append(0)
		gifts = []
		for i in range(gifts_cnt):
			line = f.readline().split()
			gifts.append(Gift(i, line[0], int(line[1]), int(line[2]), int(line[3]), int(line[4])))
	minx, maxx, miny, maxy = 0, 0, 0, 0
	for g in gifts:
		minx = min(minx, g.x)
		maxx = max(maxx, g.x)
		miny = min(miny, g.y)
		maxy = max(maxy, g.y)
	minx -= 10
	maxx += 10
	miny -= 10
	maxy += 10
	W = maxx - minx + 1
	H = maxy - miny + 1
	if W > 1000 or H > 1000:
		print(f"W = {W}, H = {H}, and it is all very big")
		quit(0)
	sc = 2 # 1000 / max(W, H)

	pygame.init()
	pygame.font.init()
	myfont = pygame.font.SysFont("Arial", 30)

	state = State(
		cur_w=0,
		carrots=0,
		cur_t=0,
		p=[0, 0],
		v=[0, 0],
		score=0,
		delivery=[0 for x in gifts], # not started, picked, delivered
		during_each_second=[[]],
		base_moments=[[0, 0]],
		error=""
	)

	states_stack = [state]

	def save_progress():
		nonlocal state
		state.error = None
		ans = []
		for v in state.during_each_second:
			ans.extend(sorted(v, key=lambda x: x[0] == "Float"))
		with open(args[1].lower() + ".out", "w") as f:
			print(len(ans), file=f)
			for line in ans:
				print(*line, file=f)
		state.error = "Successfully saved answer to " + args[1].lower() + ".out"

	def rollback():
		nonlocal states_stack
		states_stack.pop()
		# nonlocal state
		# state.error = None
		# if state.base_moments[-1][0] == state.cur_t:
		# 	state.base_moments.pop()
		# state.cur_t -= 1
		# state.during_each_second.pop()

	def accelerate(dx, dy):
		nonlocal state
		state.error = None
		if dx != 0 and dy != 0:
			state.error = f"Wrong acceleration ({dx}, {dy})"
			return
		if state.carrots == 0:
			load_carrots(1)
			if state.error:
				return
			# state.error = "You have zero carrots"
			# return
		for s in state.during_each_second[-1]:
			if s[0].startswith("Acc"):
				state.error = "You have already accelerated at this moment"
				return
		state.v[0] += dx
		state.v[1] += dy
		if dx < 0:
			state.during_each_second[-1].append(["AccLeft", abs(dx) + abs(dy)])
		elif dx > 0:
			state.during_each_second[-1].append(["AccRight", abs(dx) + abs(dy)])
		elif dy < 0:
			state.during_each_second[-1].append(["AccDown", abs(dx) + abs(dy)])
		else:
			state.during_each_second[-1].append(["AccUp", abs(dx) + abs(dy)])
		state.cur_w -= 1
		state.carrots -= 1

	def chill(t):
		nonlocal state
		state.error = None
		if state.cur_t + t > tl:
			state.error = "Too long chill"
			return
		state.during_each_second[-1].append(["Float", t])
		state.cur_t += t
		state.p[0] += state.v[0] * t
		state.p[1] += state.v[1] * t
		for i in range(t):
			state.during_each_second.append([])
		if state.p[0] ** 2 + state.p[1] ** 2 <= rad ** 2:
			state.base_moments.append([state.cur_t, state.cur_w])

	def load_carrots(cnt):
		nonlocal state
		state.error = None
		if state.base_moments[-1][1] + cnt > ws[-1]:
			state.error = "Don't have enough weight to pickup carrots"
			return
		state.base_moments[-1][1] += cnt
		state.during_each_second[state.base_moments[-1][0]].append(["LoadCarrots", cnt])
		state.carrots += cnt
		state.cur_w += cnt
		# state.cur_w += cnt
		# state.carrots += cnt
		# state.during_each_second[-1].append(["LoadCarrots", cnt])

	def load_gift(g):
		nonlocal state
		state.error = None
		# if state.p[0] ** 2 + state.p[1] ** 2 > rad ** 2:
		# 	state.error = f"Too far away ({state.p[0]}, {state.p[1]})"
		# 	return
		if state.delivery[g.id] != 0:
			state.error = "The gift is already loaded"
			return
		state.delivery[g.id] = 1
		state.cur_w += g.w
		when = state.base_moments[-1][0]
		state.base_moments[-1][1] += g.w
		state.during_each_second[when].append(["LoadGift", g.name])

	def deliver(g):
		nonlocal state
		state.error = None
		if (state.p[0] - g.x) ** 2 + (state.p[1] - g.y) ** 2 > rad ** 2:
			state.error = "Too far away"
			return
		if state.delivery[g.id] == 0:
			state.error = "The gift is not loaded"
			return
		if state.delivery[g.id] == 2:
			state.error = "The gift is already delivered"
			return
		state.delivery[g.id] = 2
		state.score += g.score
		state.cur_w -= g.w
		state.during_each_second[-1].append(["DeliverGift", g.name])

	while True:
		state = deepcopy(states_stack[-1])
		screen = pygame.display.set_mode((W * sc, H * sc))
		screen.fill((255, 255, 255))
		free_guy = pygame.Surface((sc, sc))
		free_guy.fill((0, 0, 0))
		taken_guy = pygame.Surface((sc, sc))
		taken_guy.fill((255, 0, 0))
		delivered_guy = pygame.Surface((sc, sc))
		delivered_guy.fill((0, 255, 0))
		our_body = pygame.Surface(((2 * rad + 1) * sc, (2 * rad + 1) * sc))
		our_body.fill((255, 255, 255))
		square_we_take = pygame.Surface((sc, sc))
		square_we_take.fill((0, 0, 255))
		for i in range(0, 2 * rad + 1):
			for j in range(0, 2 * rad + 1):
				if (i - rad) ** 2 + (j - rad) ** 2 <= rad ** 2:
					our_body.blit(square_we_take, (i * sc, j * sc))
		screen.blit(our_body, ((state.p[0] - minx - rad) * sc, (maxy - state.p[1] - rad) * sc))
		for g in gifts:
			screen.blit([free_guy, taken_guy, delivered_guy][state.delivery[g.id]], ((g.x - minx) * sc, (maxy - g.y) * sc))
		text = myfont.render("Time: " + str(state.cur_t) + "/" + str(tl), False, (0, 0, 0))
		screen.blit(text, (2, 2))
		text = myfont.render("Weight: " + str(state.cur_w), False, (0, 0, 0))
		screen.blit(text, (2, 35))
		text = myfont.render("Score: " + str(state.score), False, (0, 0, 0))
		screen.blit(text, (2, 68))
		text = myfont.render("Velocity: " + str(state.v), False, (0, 0, 0))
		# text = myfont.render("Action: " + str(state.during_each_second[-1]), False, (0, 0, 0))
		screen.blit(text, (2, 101))
		if state.error:
			text = myfont.render(state.error, False, (255, 0, 0))
			screen.blit(text, (2, 134))

		pygame.display.update()

		# main loop
		while 1:
			need_to_break = False
			rollbacked = False
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					pygame.quit()
					quit()
				elif event.type == pygame.KEYDOWN:
					if event.scancode == 69:
						continue
					need_to_break = True
					# print(event)
					if event.key == K_UP: # arrow up
						accelerate(0, 1)
					elif event.key == K_DOWN: # arrow down
						accelerate(0, -1)
					elif event.key == K_LEFT:
						accelerate(-1, 0)
					elif event.key == K_RIGHT:
						accelerate(1, 0)
					elif event.key == K_SPACE:
						chill(1)
					elif event.key == K_z:
						rollback()
						rollbacked = True
					elif event.key == K_s:
						save_progress()
					elif event.key == K_r:
						state = states_stack[0]
					elif event.key == K_p:
						for g in gifts:
							if (g.x - state.p[0]) ** 2 + (g.y - state.p[1]) ** 2 <= rad ** 2 and not state.delivery[g.id] and state.base_moments[-1][1] + g.w <= 40000:
								load_gift(g)
						for g in gifts:
							if state.delivery[g.id] == 1:
								deliver(g)
					elif event.key == K_c:
						load_carrots(1)
			if need_to_break:
				if not rollbacked:
					states_stack.append(state)
				break



	# pygame.font.init()
	# global myfont
	# myfont = pygame.font.SysFont("Arial", 30)
	# pygame.init()
	# while 1:
	# 	vec = play_and_click(state, pics)
	# 	while vec is None:
	# 		vec = play_and_click(state, pics)
	# 	(flag, state, data) = (0, vec[1][0], vec[1][1]) if vec[0] == "sp" else interact_galaxy(vec[1], (228, 239)) if vec[0] == "cs" else interact_galaxy(state, vec)
	# 	print(state)
	# 	while flag == 1:
	# 		print("send bobs " + str(data))
	# 		vec = send_bobs(data)
	# 		(flag, state, data) = interact_galaxy(state, vec)
	# 	pics = data


if __name__=="__main__":
	main()