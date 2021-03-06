#! /usr/bin/python3
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

from config import Config
from icgc_utils.common_queries import *
from time import time
from math import isnan

# use R functions - rpy2
from rpy2.robjects.packages import importr
# in particular, p-value under hypergeometric distribution
phyper = importr('stats').phyper


####################################################
def silent_count(cursor, table, stats_id):
	# TODO: why am I setting pathogenicity_estimate=1 here?
	retlines = []
	qry  = "select  gene_symbol,  count(distinct(icgc_donor_id)) from %s " % table
	qry += "where pathogenicity_estimate=1 and reliability_estimate=1 "
	qry += "and not gene_symbol is null "
	qry += "group by gene_symbol"
	# Under Python 3.6, the built-in dict does track insertion order,
	# although this behavior is a side-effect of an implementation change and should not be relied on.
	genes_mutated = dict(sorted(error_intolerant_search(cursor, qry), key= lambda r: r[1], reverse=True))
	retlines.append("affected genes %d " % len(genes_mutated))
	retlines_per ={}
	pval_per = {}
	stn_per  = {}
	exp_per  = {}
	for gene, ct in list(genes_mutated.items())[:100]:
		retlines_per[gene] = []
		retlines_per[gene].append("\n%-10s  mutated %d times" % (gene, ct))
		silent_possible, nonsilent_possible = silent_nonsilent_retrieve(cursor, gene)
		if silent_possible<0: continue # this signals some problem with the submitted cdan sequence
		retlines_per[gene].append("\t %s all possible:  silent %d    nonsilent %d    silent/nonsilent %.3f    silent/(silent+nonsilent) %.3f " %
						(gene, silent_possible, nonsilent_possible, silent_possible/nonsilent_possible,
						 silent_possible/(silent_possible+nonsilent_possible) ))
		expected_silent_to_nonsilent = silent_possible/nonsilent_possible
		chromosome = find_chromosome(cursor, gene)
		qry  = "select m.mutation_type, count(*) c from  %s s, mutations_chrom_%s m where s.gene_symbol = '%s' " % (table, chromosome, gene)
		qry += "and s.icgc_mutation_id=m.icgc_mutation_id  "
		qry += "and s.pathogenicity_estimate=1 and s.reliability_estimate=1  "
		qry += "group by m.mutation_type"
		ret = error_intolerant_search(cursor, qry)
		if not ret or len(ret)==0: continue
		type_count = dict(ret)
		for muttype, ct in type_count.items():
			retlines_per[gene].append("\t\t {}: {}".format(muttype, ct))
			if muttype != 'single': continue
			qry = "select m.consequence, count(*) c from  %s s, mutations_chrom_%s m where s.gene_symbol = '%s' " % (table, chromosome, gene)
			qry += "and s.icgc_mutation_id=m.icgc_mutation_id  and m.mutation_type='single'  "
			# we want silent mutations here, that are already marked with pathg 0 (thus drop pathg=1 filter)
			qry += "and s.reliability_estimate=1  "
			qry += "group by m.consequence"
			ret = error_intolerant_search(cursor, qry)
			if not ret or len(ret)==0: continue
			conseq_ct = dict(ret)
			nonsilent = conseq_ct.get('missense',0) + conseq_ct.get('stop_gained',0) + conseq_ct.get('stop_lost',0)
			if nonsilent==0: continue
			silent = conseq_ct.get('synonymous',0)
			if silent+nonsilent==0: continue
			for conseq, ct in conseq_ct.items():
				retlines_per[gene].append("\t\t\t\t {}: {}".format(conseq, ct))
			silent_to_nonsilent  = float(silent)/nonsilent if nonsilent>0 else 1.0
			# pvalue under hypergeometric distribution (R)
			# https://stackoverflow.com/questions/8382806/hypergeometric-test-phyper
			# phyper(success in sample, success in population, failure in population, sample size)
			# that is
			# phyper(silent, silent_possible, nonsilent_possible, silent+nonsilent)
			phyper_ret = phyper(silent, silent_possible, nonsilent_possible, silent+nonsilent)
			pval = phyper_ret[0] if phyper_ret  and not isnan(phyper_ret[0]) else 1.0
			retlines_per[gene].append("\t\t silent/nonsilent = %.3f    expected = %.3f    pval = %.0e" %
			                    (silent_to_nonsilent, expected_silent_to_nonsilent, pval))
			stn_per[gene]  = silent_to_nonsilent
			pval_per[gene] = pval
			exp_per[gene]  = expected_silent_to_nonsilent

	genes_sorted = sorted(pval_per.keys(), key=lambda g: pval_per[g], reverse=False)
	tumor_short = table.split('_')[0]
	for gene in genes_sorted:
		if pval_per[gene]>0.5: continue
		retlines_per[gene][0] = "\n%3d %s   %.0e" % (genes_sorted.index(gene), retlines_per[gene][0].strip(), pval_per[gene])
		retlines.extend(retlines_per[gene])

		parameters = "{};{}".format(tumor_short, gene)
		stats_string = "%.3f;%.3f;%.0e"% (stn_per[gene],  exp_per[gene], pval_per[gene])
		print("storing", parameters, stats_string)
		store_without_checking(cursor, 'stats',{'stats_id':stats_id, 'parameters':parameters, 'stats':stats_string})

	return retlines


######################################
def store_stats_description(cursor, stats_id):
	fixed_fields  = {'stats_id':stats_id}
	descr = "Silent-to-nonsilent ratio of single nucleotide mutations in the canonical splice, together with the expected value and the p-value."
	update_fields = {'description':descr,
					'parameters':"tumor_short:string;gene_symbol:string",
					'stats':"observed_ratio:float;expected_ratio:float;pval:double"}
	store_or_update(cursor, 'stats_description', fixed_fields, update_fields)

############################
def main():

	db     = connect_to_mysql(Config.mysql_conf_file)
	cursor = db.cursor()
	switch_to_db(cursor, 'icgc')
	stats_id = "silence"
	store_stats_description(cursor, stats_id)

	outdir = "genes"

	#########################
	# which simple somatic tables do we have
	qry  = "select table_name from information_schema.tables "
	qry += "where table_schema='icgc' and table_name like '%_simple_somatic'"
	tables = [field[0] for field in  search_db(cursor,qry)]

	for table in tables:
	#for tumor_short in ['AML']:
		print(table)
		tumor_short = table.replace("_simple_somatic",'')
		os.makedirs("{}/{}".format(outdir, tumor_short),exist_ok=True)
		time0 = time()
		outf = open("{}/{}/silent_nonsilent.txt".format(outdir, tumor_short), "w")
		outf.write("\n=============================\n")
		outf.write(tumor_short+"\n")
		outf.write("total donors: {}\n".format(len(get_donors(cursor, table))))
		retlines = silent_count(cursor, table, stats_id)
		if retlines: outf.write("\n".join(retlines)+"\n")
		outf.close()
		print("\t done in  %.2f mins" % (float(time()-time0)/60))
	cursor.close()
	db.close()

	return


#########################################
if __name__ == '__main__':
	main()
