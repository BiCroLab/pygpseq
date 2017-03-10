# -*- coding: utf-8 -*-

""" Functions for the management of strings """

def add_trailing_new_line(s):
	""" Adds trailing new line """
	if '\n' != s[len(s) - 1]:
		s += '\n'
	return(s)

def add_leading_dot(s, not_empty = None):
	"""
	Adds leading dot.

	@param:
	 - s <string> string to recieve leading dot
	 - not_empty <boolean> whether to add leading dot to empty string
	"""
	if None == not_empty:
		not_empty = True
	if 0 == len(s) and not_empty:
		return(s)
	if not s.startswith('.'):
		s = '.' + s
	return(s)
