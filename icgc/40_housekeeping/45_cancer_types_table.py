#!/usr/bin/python3
#
# This source code is part of icgc, an ICGC processing pipeline.
# 
# Icgc is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Icgc is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program. If not, see<http://www.gnu.org/licenses/>.
# 
# Contact: ivana.mihalek@gmail.com
#

# problem: this does not include tcga tables

from icgc_utils.utils import cancer_dictionary

def main():

	cd = cancer_dictionary()

	for cancer_type,dict  in cd.items():
		print("%s\t%s\t%s" % (cancer_type, dict["subtypes"], dict["description"]))


	return

#########################################
if __name__ == '__main__':
	main()
