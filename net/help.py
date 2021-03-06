"""
tfnet secondary (helper) methods
"""
from utils.loader import create_loader
from time import time as timer
import tensorflow as tf
import numpy as np
# import skvideo.io
# import skimage.io
import sys
import cv2
import os

old_graph_msg = 'Resolving old graph def {} (no guarantee)'

def build_train_op(self):
	self.framework.loss(self.out)
	self.say('Building {} train op'.format(self.meta['model']))
	optimizer = self._TRAINER[self.FLAGS.trainer](self.FLAGS.lr)
	gradients = optimizer.compute_gradients(self.framework.loss)
	self.train_op = optimizer.apply_gradients(gradients)

def load_from_ckpt(self):
	if self.FLAGS.load < 0: # load lastest ckpt
		with open(self.FLAGS.backup + 'checkpoint', 'r') as f:
			last = f.readlines()[-1].strip()
			load_point = last.split(' ')[1]
			load_point = load_point.split('"')[1]
			load_point = load_point.split('-')[-1]
			self.FLAGS.load = int(load_point)
	
	load_point = os.path.join(self.FLAGS.backup, self.meta['name'])
	load_point = '{}-{}'.format(load_point, self.FLAGS.load)
	self.say('Loading from {}'.format(load_point))
	try: self.saver.restore(self.sess, load_point)
	except: load_old_graph(self, load_point)

def say(self, *msgs):
	if not self.FLAGS.verbalise:
		return
	msgs = list(msgs)
	for msg in msgs:
		if msg is None: continue
		print msg

def load_old_graph(self, ckpt):	
	ckpt_loader = create_loader(ckpt)
	self.say(old_graph_msg.format(ckpt))
	
	for var in tf.global_variables():
		name = var.name.split(':')[0]
		args = [name, var.get_shape()]
		val = ckpt_loader(args)
		assert val is not None, \
		'Cannot find and load {}'.format(var.name)
		shp = val.shape
		plh = tf.placeholder(tf.float32, shp)
		op = tf.assign(var, plh)
		self.sess.run(op, {plh: val})

def camera(self, file):
	swap = file != 'camera'
	if not swap: camera = cv2.VideoCapture(0)
	# else:
	# 	camera = skvideo.io.VideoCapture(file, (448, 448))
	# 	writer = cv2.VideoWriter(
	# 		'{}-out.avi'.format(file), -1, 20.0, (448,448))
	self.say('Press [ESC] to quit demo')
	assert camera.isOpened(), \
	'Cannot capture source'

	elapsed = int()
	start = timer()
	while camera.isOpened():
		_, frame = camera.read()
		preprocessed = self.framework.preprocess(frame)
		net_out = self.sess.run(self.out, 
					feed_dict = {self.inp: [preprocessed] 
				})[0]
		processed = self.framework.postprocess(
			net_out, frame, False)
		if swap:
			processed = cv2.cvtColor(
				processed, cv2.COLOR_BGR2RGB)
			writer.write(frame)
		#else: 
		cv2.imshow('', processed)
		elapsed += 1
		if elapsed % 5 == 0:
			sys.stdout.write('\r')
			sys.stdout.write('{0:3.3f} FPS'.format(
				elapsed / (timer() - start)))
			sys.stdout.flush()
		choice = cv2.waitKey(1)
		if choice == 27: break

	sys.stdout.write('\n')
	camera.release()
	cv2.destroyAllWindows()

def to_darknet(self):
	darknet_ckpt = self.darknet
	with self.graph.as_default() as g:
		for var in tf.global_variables():
			name = var.name.split(':')[0]
			var_name = name.split('-')
			l_idx = int(var_name[0])
			w_sig = var_name[1].split('/')[-1]
			l = darknet_ckpt.layers[l_idx]
			l.w[w_sig] = var.eval(self.sess)

	for layer in darknet_ckpt.layers:
		for ph in layer.h:
			feed = self.feed[layer.h[ph]]
			layer.h[ph] = feed

	return darknet_ckpt