#!/usr/bin/python
import os
import csv
import copy

from optparse import OptionParser

# --------------------------------------------------------
# Joep de Ligt
# Build for Python 2.7
# Parse ThermoFisher Open Array CSV file to per sample VCF
# --------------------------------------------------------

parser = OptionParser()
parser.add_option("--csv",	dest="csv_file", help="Path to CSV to convert", default=False)
parser.add_option("--out",	dest="out_dir", help="Path to output VCF files", default=False)
parser.add_option("--des",	dest="design_vcf", help="Path to design template VCF, see Generate_VCF_Template.py",	default=False)
(options, args) = parser.parse_args()

# --------------------------------------------------------


# ---------------------- CSV FORMAT ----------------------
# Sample_ID,Plate_Barcode,Gene_Symbol,NCBI_SNP_Reference,Assay_Name_or_ID,Allele_1_Call,Allele_2_Call
# A1_HUB-02-B2-032_2,THF94,NULL,rs4855056,C_11821218_10,NOAMP,NOAMP

# ----------------------VCF FORMAT ----------------------
# ##fileformat=VCFv4.1
# #CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	TEST
# 1	59569829	.	C	T	225	.	DP=133;VDB=0.0504;AF1=0.5;AC1=1;DP4=20,37,21,47;MQ=59;FQ=225;PV4=0.7,1,1,1	GT:PL:DP:GQ	


# --------------------------------------------------------

def CheckArguments(options):
	#print("Checking arguments")
	if not options.csv_file or not os.path.exists(options.csv_file):
		print("Invalid VCF file %s"%(options.csv_file))
		return False
	
	# ---- SNV file ---
	if not options.out_dir or not os.path.exists(options.out_dir):
		print("Invalid OUTPUT directory %s"%(options.out_dir))
		return False

	if not options.design_vcf or not os.path.exists(options.design_vcf):
		print("Invalid DESIGN VCF file %s"%(options.design_vcf))
		return False

	return True

def IsHeader(row, head):
	return ' '.join(row).startswith(head)
	
# --------------------------------------------------------

def ReadFileById(filename, ftype):
	headers = []
	data = {}
	
	delim, key, head = False, False, False
	
	if ftype is 'csv':
		delim = ','
		key = 'NCBI_SNP_Reference'
		head = ' #'
	
	if ftype is 'vcf':
		delim = '\t'
		key = 'ID'
		head = '##'

	# Open in unversial mode to enable windows line endings
	with open(filename, 'rU') as f:
		reader = csv.reader((f), delimiter=delim)

		# read header lines
		row = reader.next()

		while IsHeader(row, head):
			headers.append(delim.join(row))
			row = reader.next()
		
		# read empty lines
		while len(row) <= 1:
			row = reader.next()	

		# fix column headers
		row = [heading.replace(" ","_") for heading in row]
		# store column names
		colnames = row


		for row in reader:
			if len(row) <= 1:
				continue

			dicto = dict(zip(colnames,row))

			sample_id = False
			if ftype is 'vcf':
				sample_id = colnames[-1]
			if ftype is 'csv':
				sample_id = dicto['Sample_ID']

			sample_id = sample_id.replace(" ","").replace("_","-").replace("/","-").replace("\\","-")
			sample_id = sample_id.replace("---","-").replace("--","-")

			if ftype is 'csv':
				sample_id = sample_id+"_"+dicto['Plate_Barcode']

			if sample_id not in data:
				data[sample_id] = {}
			
			data[sample_id][dicto[key]] = dicto

	return [headers, colnames, data]

# --------------------------------------------------------

def DetermineGenotype(vcf, entry):
	# FAILED indicators
	failed = ["UND","NOAMP"]
	# REF / ALT determination
	ref = entry["Allele_1_Call"]
	alt = entry["Allele_2_Call"]
	geno = False
	alto = alt

	# return FAILED	
	if ref in failed or alt is failed:
		geno = "./.:0"
		alto = vcf["ALT"]
		return [alto, geno]


	# IF ref call matches VCF ref		
	if ref is vcf["REF"]:
		if alt is ref:
			geno = "0/0"
		else:
			geno = "0/1"

	else:
		if alt is ref:
			geno = "1/1"
		elif alt is vcf["REF"]:
			geno = "0/1"
			alto = ref
		else:
			print("[WARNING] incompatible calls with TEMPLATE vcf")
			print(ref,alt,vcf)


	return [alto, geno+":60"]

# --------------------------------------------------------

def Main():
	if not CheckArguments(options):
		print("Error in provided arguments")
		exit(0)

	csv_headers, csv_cols, csv_data = ReadFileById(options.csv_file, 'csv')
	vcf_headers, vcf_cols, vcf_data = ReadFileById(options.design_vcf, 'vcf')

	# Write VCF for each Experiment in Open Array result set
	for sample in csv_data:
		outfile = open(os.path.join(options.out_dir,sample+"_OpenArrayCalls"+".vcf"),'w')

		outfile.write('\n'.join(vcf_headers)+'\n')
		outfile.write('\n#'.join(csv_headers))

		tmp_vcf_cols = copy.copy(vcf_cols)
		tmp_vcf_cols[-1] = sample
		outfile.write('\t'.join(tmp_vcf_cols)+'\n')

		template = vcf_data['TEST']
	
		# TODO order output by genomic position
		for position in template:
			this_vcf = []
			for col in vcf_cols:
				this_vcf.append(template[position][col])

			# ALT        FORMAT [GT:GQ]
			this_vcf[4], this_vcf[-1] = DetermineGenotype(template[position], csv_data[sample][position])
			
			outfile.write('\t'.join(this_vcf)+'\n')

		outfile.close()

	#print csv_data
	#print "-"*100
	#print vcf_data
	#print "-"*100

if __name__ == "__main__":
	Main()

