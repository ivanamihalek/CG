#!/usr/bin/python

import MySQLdb
from   tcga_utils.mysql   import  *
import commands

#########################################
def make_meta_table(cursor, db_name, meta_table):
    
    switch_to_db (cursor, db_name)
    qry = ""
    qry += "  CREATE TABLE  %s (" % meta_table
    qry += "     id INT NOT NULL AUTO_INCREMENT, "
    qry += "	 file_name BLOB NOT NULL, "
    qry += "	 quality_check VARCHAR (10), " # pass or fail
    qry += "	 assembly VARCHAR (10), "
    qry += "	 diagnostics BLOB, "
    qry += "	 PRIMARY KEY (id) "
    qry += ") ENGINE=MyISAM"
    rows = search_db(cursor, qry)
    print qry
    print rows

#########################################
def make_mutations_table(cursor, db_name, mutations_table):

    switch_to_db (cursor, db_name)

    qry = ""
    qry += "  CREATE TABLE  %s (" % mutations_table
    qry += "     id INT NOT NULL AUTO_INCREMENT, "
    qry += "  	 hugo_symbol VARCHAR (50) NOT NULL, "
    qry += "     entrez_gene_id INT, "
    qry += "	 aa_change VARCHAR (100), "
    qry += "	 cdna_change BLOB, "
    qry += "	 chromosome VARCHAR (20) NOT NULL, "
    qry += "	 start_position INT  NOT NULL, "
    qry += "	 end_position INT NOT NULL, "
    qry += "	 strand VARCHAR (5) NOT NULL, "
    qry += "	 variant_classification VARCHAR (50) NOT NULL, "
    qry += "	 variant_type VARCHAR (20) NOT NULL, "
    qry += "	 reference_allele BLOB NOT NULL, "
    qry += "	 tumor_seq_allele1 BLOB NOT NULL, "
    qry += "	 tumor_seq_allele2 BLOB NOT NULL, "
    qry += "	 tumor_sample_barcode VARCHAR (50) NOT NULL, "
    qry += "	 sample_barcode_short VARCHAR (20) NOT NULL, "
    qry += "	 matched_norm_sample_barcode VARCHAR (50) NOT NULL, "
    qry += "	 match_norm_seq_allele1 BLOB, "
    qry += "	 match_norm_seq_allele2 BLOB, "
    qry += "	 tumor_validation_allele1 BLOB, "
    qry += "	 tumor_validation_allele2 BLOB, "
    qry += "	 match_norm_validation_allele1 BLOB, "
    qry += "	 match_norm_validation_allele2 BLOB, "
    qry += "	 verification_status VARCHAR (20), "
    qry += "	 validation_status VARCHAR (20) NOT NULL, "
    qry += "	 mutation_status VARCHAR (50) NOT NULL, "
    qry += "	 meta_info_index INT (11)  NOT NULL, "
    qry += "	 conflict BLOB, "
    qry += "	 PRIMARY KEY (id) "
    qry += ") ENGINE=MyISAM"

    rows = search_db(cursor, qry)
    print qry
    print rows

    qry = ""
    qry += "create index hugo_idx on %s (hugo_symbol)" % mutations_table
    rows = search_db(cursor, qry)
    print qry
    print rows

    qry = ""
    qry += "create index mutation_idx on %s (sample_barcode_short, chromosome, start_position)" % mutations_table
    rows = search_db(cursor, qry)
    print qry
    print rows

#########################################
def add_column_to_mutations_table(cursor, db_name, new_column,  mutations_table):

    switch_to_db (cursor, db_name)
    qry = "select database()"
    rows = search_db(cursor, qry)
    print qry
    print rows

    qry = "";
    qry += "  ALTER TABLE %s ADD COLUMN"  % mutations_table
    qry += "	%s  BLOB " % new_column
    rows = search_db(cursor, qry)
    print qry
    print rows

#########################################
def main():
    
    db     = connect_to_mysql()
    cursor = db.cursor()

    db_names  = ["ACC", "BLCA", "BRCA", "CESC", "CHOL",  "COAD", "DLBC", "ESCA", "GBM", "HNSC", "KICH" ,"KIRC",
                 "KIRP", "LAML", "LGG", "LIHC", "LUAD", "LUSC",  "MESO", "OV",   "PAAD", "PCPG", "PRAD", "REA",
                 "SARC", "SKCM", "STAD", "TGCT", "THCA", "THYM", "UCEC", "UCS", "UVM"]


    for db_name in db_names:
        # check db exists
        qry = "show databases like '%s'" % db_name
        rows = search_db(cursor, qry)
        if not rows:
            print db_name, "not found"
            qry = "create database " +  db_name
            rows = search_db(cursor, qry)
            print qry
            print rows
            make_mutations_table (cursor, db_name, mutations_table)

        print " ** ", db_name
        switch_to_db (cursor, db_name)
        qry = "show tables"
        rows = search_db(cursor, qry)
        print qry
        print rows
      
        meta_table = "mutations_meta"
        if ( check_table_exists (cursor, db_name, meta_table)):
            print meta_table, " found in ", db_name
        else:
            make_meta_table(cursor, db_name, meta_table)

        for mutations_table in ( 'somatic_mutations', 'metastatic_mutations'):
            if ( check_table_exists (cursor, db_name, mutations_table)):
                print mutations_table, " found in ", db_name
            else:
                print mutations_table, " not found in ", db_name
            
                make_mutations_table(cursor, db_name, mutations_table)
                qry = ""
                qry += "create index variant_idx on %s (hugo_symbol, variant_classification)" % mutations_table
                rows = search_db(cursor, qry)
                print qry
                print rows


    cursor.close()
    db.close()


#########################################
if __name__ == '__main__':
    main()
