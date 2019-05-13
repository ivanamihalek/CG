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
# along with this program. If not, see <http://www.gnu.org/licenses/>.
# 
# Contact: ivana.mihalek@gmail.com
#

import time


from icgc_utils.common_queries  import  *
from icgc_utils.icgc import *
from icgc_utils.processes import *
from config import Config


tcga_icgc_table_correspondence = {
	"ACC_somatic_mutations" :  "ACC_simple_somatic",
	"ALL_somatic_mutations" :  "ALL_simple_somatic",
	"BLCA_somatic_mutations": "BLCA_simple_somatic",
	"BRCA_somatic_mutations": "BRCA_simple_somatic",
	"CESC_somatic_mutations": "CESC_simple_somatic",
	"CHOL_somatic_mutations": "CHOL_simple_somatic",
	"COAD_somatic_mutations": "COCA_simple_somatic",
	"DLBC_somatic_mutations": "DLBC_simple_somatic",
	"ESCA_somatic_mutations": "ESAD_simple_somatic",
	"GBM_somatic_mutations" :  "GBM_simple_somatic",
	"HNSC_somatic_mutations": "HNSC_simple_somatic",
	"KICH_somatic_mutations": "KICH_simple_somatic",
	"KIRC_somatic_mutations": "KIRC_simple_somatic",
	"KIRP_somatic_mutations": "KIRP_simple_somatic",
	"LAML_somatic_mutations":  "AML_simple_somatic",
	"LGG_somatic_mutations" :  "LGG_simple_somatic",
	"LIHC_somatic_mutations": "LICA_simple_somatic",
	"LUAD_somatic_mutations": "LUAD_simple_somatic",
	"LUSC_somatic_mutations": "LUSC_simple_somatic",
	"MESO_somatic_mutations": "MESO_simple_somatic",
	"OV_somatic_mutations"  :   "OV_simple_somatic",
	"PAAD_somatic_mutations": "PACA_simple_somatic",
	"PCPG_somatic_mutations": "PCPG_simple_somatic",
	"PRAD_somatic_mutations": "PRAD_simple_somatic",
	"READ_somatic_mutations": "COCA_simple_somatic",
	"SARC_somatic_mutations": "SARC_simple_somatic",
	"SKCM_somatic_mutations": "MELA_simple_somatic",
	"STAD_somatic_mutations": "GACA_simple_somatic",
	"TGCT_somatic_mutations": "TGCT_simple_somatic",
	"THCA_somatic_mutations": "THCA_simple_somatic",
	"THYM_somatic_mutations": "THYM_simple_somatic",
	"UCEC_somatic_mutations": "UCEC_simple_somatic",
	"UCS_somatic_mutations" : "UTCA_simple_somatic",
	"UVM_somatic_mutations" :  "UVM_simple_somatic"
}


variant_columns = ['icgc_mutation_id', 'chromosome','icgc_donor_id', 'icgc_specimen_id', 'icgc_sample_id',
				   'submitted_sample_id','control_genotype', 'tumor_genotype', 'total_read_count', 'mutant_allele_read_count']


# we'll take care of 'aa_mutation' and 'consequence_type will be handled separately
mutation_columns = ['icgc_mutation_id', 'start_position', 'end_position', 'mutation_type',
					'mutated_from_allele', 'mutated_to_allele', 'reference_genome_allele']

location_columns = ['position', 'gene_relative', 'transcript_relative']

################################################################
# stop_retained: A sequence variant where at least one base in the terminator codon is changed, but the terminator remains
consequence_vocab = ['stop_lost', 'synonymous', 'inframe_deletion', 'inframe_insertion', 'stop_gained',
					 '5_prime_UTR_premature_start_codon_gain',
					 'start_lost', 'frameshift', 'disruptive_inframe_deletion', 'stop_retained',
					 'exon_loss', 'disruptive_inframe_insertion', 'missense']

# location_vocab[1:4] is gene-relative
# location_vocab[1:4] is transcript-relative
location_vocab = ['intergenic_region', 'intragenic', 'upstream', 'downstream',
				  '5_prime_UTR', 'exon',  'coding_sequence', 'initiator_codon',
				  'splice_acceptor', 'splice_region', 'splice_donor',
				  'intron', '3_prime_UTR', ]

# this is set literal
pathogenic = {'stop_lost', 'inframe_deletion', 'inframe_insertion', 'stop_gained', '5_prime_UTR_premature_start_codon_gain',
					 'start_lost', 'frameshift', 'disruptive_inframe_deletion',
					 'exon_loss', 'disruptive_inframe_insertion', 'missense',
					 'splice_acceptor', 'splice_region', 'splice_donor', 'inframe'
			 }


#########################################
# to make things easier for us it looks like there is some
# disagreement between TCGA and ICGC what is specimen and what is sample
# TCGA sample codes seem to correspond to ICGC specimen types
# https://docs.gdc.cancer.gov/Encyclopedia/pages/TCGA_Barcode/

#########################################
def tcga_sample2tcga_donor(s):
	return "-".join(s.split("-")[:3])

#########################################
def sample_id_from_TCGA_barcode(sample_barcode):
	pieces = sample_barcode.split("-")
	sample_id = "-".join(pieces[:4])
	# the last character here is a "vial"
	# so we'll just use this as both 'specimen' and 'sample' id
	return sample_id

#########################################
def specimen_type_from_TCGA_barcode(sample_barcode):
	# we want to translate this to something similar to what ICGC is using
	# roughly: Normal, Primary, Metastatic, Recurrent, Cell_line
	tcga_sample_code = sample_barcode.split("-")[3][:2]
	if tcga_sample_code in ['01','03','05', '09']:
		return 'Primary'

	elif tcga_sample_code in ['02','04','40']:
		return 'Recurrent'

	elif tcga_sample_code in ['06','07']:
		return 'Metastatic'

	elif tcga_sample_code in ['10','11','12','13','14']:
		return 'Normal'

	elif tcga_sample_code in ['08','50']:
		return 'Cell_line'

	return "Other"

#########################################
def quotify(something):
	if not something:
		return ""
	if type(something)==str:
		return "\'"+something+"\'"
	else:
		return str(something)


#########################################
def check_location_stored(cursor, tcga_named_field):
	location_table = "icgc.locations_chrom_%s" % tcga_named_field['chromosome']
	qry = "select count(*) from %s where position=%s"%(location_table, tcga_named_field['start_position'])
	ret = search_db(cursor,qry)
	if ret and len(ret)>1:
		print("problem: non-unique location id")
		print(qry)
		print(ret)
		exit()
	return False if not ret else True


#########################################
def find_mutation_id(cursor, tcga_named_field):
	mutation_table = "mutations_chrom_%s" % tcga_named_field['chromosome']
	qry = "select icgc_mutation_id, pathogenicity_estimate from icgc.%s where start_position=%s "%(mutation_table, tcga_named_field['start_position'])
	reference_allele = tcga_named_field['reference_allele']
	differing_allele = tcga_named_field['tumor_seq_allele1']
	if differing_allele == reference_allele: differing_allele = tcga_named_field['tumor_seq_allele2']
	if len(reference_allele)>200: reference_allele=reference_allele[:200]+"etc"
	if len(differing_allele)>200: differing_allele=differing_allele[:200]+"etc"
	qry += "and mutated_from_allele='%s' and mutated_to_allele='%s' "%(reference_allele,differing_allele)
	ret = search_db(cursor,qry)

	if not ret: return # we skipped intergenic mutations

	if len(ret)>1:
		print("problem: non-unique mutation id")
		print(qry)
		print(ret)
		exit()
	return False if not ret else ret[0]



#########################################
def store_specimen_info(cursor, tumor_short, donor_id, tcga_barcode):
	fixed_fields  = {'icgc_donor_id':donor_id, 'icgc_specimen_id': sample_id_from_TCGA_barcode(tcga_barcode)}
	update_fields = {'specimen_type':specimen_type_from_TCGA_barcode(tcga_barcode)}
	store_or_update(cursor, "%s_specimen"%tumor_short, fixed_fields, update_fields)
	return


#########################################
def store_donor_info(cursor, tumor_short, donor_id, tcga_barcode):
	fixed_fields  = {'icgc_donor_id':donor_id, 'submitted_donor_id': tcga_sample2tcga_donor(tcga_barcode)}
	update_fields = None
	store_or_update(cursor, "%s_donor"%tumor_short, fixed_fields, update_fields)
	return


#########################################
def store_variant(cursor, tcga_named_field, mutation_id, pathogenicity_estimate, icgc_variant_table):

	#have we stored this by any chance?
	qry  = "select submitted_sample_id from icgc.%s " % icgc_variant_table
	qry += "where icgc_mutation_id='%s' " % mutation_id
	ret = search_db(cursor,qry)
	tcga_participant_id = tcga_sample2tcga_donor(tcga_named_field['tumor_sample_barcode'])
	if ret and (tcga_participant_id in [tcga_sample2tcga_donor(r[0]) for r in ret]): return

	new_donor_id = tcga_participant_id
	tumor_short = icgc_variant_table.split("_")[0]
	# this is redundant, but then the specimen table is small ...
	store_specimen_info(cursor, tumor_short, new_donor_id, tcga_named_field['tumor_sample_barcode'])
	store_donor_info(cursor, tumor_short, new_donor_id, tcga_named_field['tumor_sample_barcode'])
	# tcga could not agree with itself in which column to place the cancer allele
	reference_allele = tcga_named_field['reference_allele']
	differing_allele = tcga_named_field['tumor_seq_allele1']
	if differing_allele == reference_allele: differing_allele = tcga_named_field['tumor_seq_allele2']
	if len(reference_allele)>200: reference_allele=reference_allele[:200]+"etc"
	if len(differing_allele)>200: differing_allele=differing_allele[:200]+"etc"

	# if variants from this same donor exist under different sample/specimen heading we will have to
	# reove duplicates downstream
	icgc_specimen_id = icgc_sample_id = sample_id_from_TCGA_barcode(tcga_named_field['tumor_sample_barcode'])

	# fill store hash
	store_fields = {
		'icgc_mutation_id': mutation_id,
		'chromosome': tcga_named_field['chromosome'],
		'icgc_donor_id': new_donor_id,
		'icgc_specimen_id': icgc_specimen_id,
		'icgc_sample_id': icgc_sample_id,
		'submitted_sample_id': tcga_named_field['tumor_sample_barcode'],
		'tumor_genotype': "{}/{}".format(reference_allele,differing_allele),
		'pathogenicity_estimate': pathogenicity_estimate,
		'reliability_estimate': 1
	}
	# store - we actually checked above
	store_without_checking(cursor, icgc_variant_table, store_fields, verbose=False, database='icgc')

	return


#########################################
def process_tcga_table(cursor, tcga_table, icgc_table, already_deposited_in_icgc):

	standard_chromosomes = [str(i) for i in range(23)] +['X','Y']
	no_rows = search_db(cursor,"select count(*) from tcga.%s"% tcga_table)[0][0]

	column_names = get_column_names(cursor,'tcga',tcga_table)
	qry = "select * from tcga.%s " % tcga_table
	ct = 0
	time0 = time.time()

	for row in search_db(cursor,qry):
		ct += 1
		if (ct%50000==0):
			print("%30s   %6d lines out of %6d  (%d%%)  %d min" % \
				(tcga_table, ct, no_rows, float(ct)/no_rows*100, float(time.time()-time0)/60))
		named_field = dict(list(zip(column_names,row)))
		if not named_field['chromosome'] in standard_chromosomes: continue
		if tcga_sample2tcga_donor(named_field['tumor_sample_barcode']) in already_deposited_in_icgc: continue

		# we should have stored the mutation in one of the previous steps (scripts, 'reorganize_mutations' or some such)
		ret = find_mutation_id(cursor, named_field)
		if not ret: continue # intergenic mutations not stored
		mutation_id, pathogenicity_estimate = ret
		location_is_stored = check_location_stored(cursor, named_field)
		# if location not stored, this is intergenic
		if not location_is_stored: continue
		if not mutation_id:
			print("mutation id not found for:  ", named_field)
			continue
		# all clear - store
		store_variant(cursor, named_field, mutation_id, pathogenicity_estimate, icgc_table)


#########################################
def add_tcga_diff(tcga_tables, other_args):

	db     = connect_to_mysql(Config.mysql_conf_file)
	cursor = db.cursor()
	for tcga_table in tcga_tables:

		icgc_table =  tcga_icgc_table_correspondence[tcga_table]
		tumor = icgc_table.split("_")[0]
		# where in the icgc classification does this symbol belong?
		time0 = time.time()
		print("\n"+"-"*50+"\npid {} processing tcga table {} - will be stored in {}".\
				format(os.getpid(), tcga_table,  icgc_table))
		#tcga donors already deposited in icgc - we may have dropped some of them in one of the duplicated removal rounds
		# (thus we go back to *_temp tables)
		already_deposited_in_icgc = ()
		if check_table_exists(cursor, "icgc", "{}_temp".format(icgc_table)):
			qry  = "select distinct(submitted_sample_id) from icgc.{}_temp ".format(icgc_table)
			qry += "where submitted_sample_id like '{}' or  submitted_sample_id like '{}' ".format("TCGA_%", "TARGET_%")
			ret = search_db(cursor,qry)
			if ret: already_deposited_in_icgc = [tcga_sample2tcga_donor(r[0]) for r in ret]
		process_tcga_table(cursor, tcga_table, icgc_table,  already_deposited_in_icgc)
		print("\t overall time for %s: %.3f mins; pid: %d" % (tcga_table, float(time.time()-time0)/60, os.getpid()))

	cursor.close()
	db.close()

	return


#########################################
#########################################
def main():

	# divide by cancer types, because I have duplicates within each cancer type
	# that I'll resolve as I go, but I do not want the threads competing)
	db     = connect_to_mysql(Config.mysql_conf_file)
	cursor = db.cursor()

	qry  = "select table_name from information_schema.tables "
	qry += "where table_schema='tcga' and table_name like '%_somatic_mutations'"
	tcga_tables = [field[0] for field in search_db(cursor,qry)]
	for tcga_table in tcga_tables:
		icgc_table =  tcga_icgc_table_correspondence[tcga_table]
		tumor = icgc_table.split("_")[0]
		# change id fields to autoincrement if ther are not
		# (we needed them not to be autoincrement to read in from tsv)
		set_autoincrement(cursor, 'icgc',  "{}_donor".format(tumor), 'id')
		set_autoincrement(cursor, 'icgc',  "{}_specimen".format(tumor), 'id')

	number_of_chunks = 12

	parallelize(number_of_chunks, add_tcga_diff, tcga_tables, [])


#########################################
if __name__ == '__main__':
	main()
