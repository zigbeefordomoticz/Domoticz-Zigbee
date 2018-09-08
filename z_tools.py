"""
	Module : z_tools.py

	Description: Zigate toolbox
"""


def returnlen(taille , value) :
	while len(value)<taille:
		value="0"+value
	return str(value)


def Hex_Format(taille, value):
	value = hex(int(value))[2:]
	if len(value) > taille:
		return 'f' * taille
	while len(value)<taille:
		value="0"+value
	return str(value)
