# -*- coding: utf-8 -*-
#!/usr/bin/env python
import os
import boto3
import requests
from operator import itemgetter
from jinja2 import Template, Environment, FileSystemLoader

class  Info:

	iam = requests.get("http://169.254.169.254/latest/dynamic/instance-identity/document")

	def __init__(self):

		#Instance own info
		self.myid = str(Info.iam.json()['instanceId'])
		self.myip = str(Info.iam.json()['privateIp'])
		self.region = str(Info.iam.json()['region'])

	def _aws(self, filters=None):
		"""
		Connect to aws and retrieve info about the instance or
		group of instances
		"""

		#aws client connection
		self.client = boto3.client('ec2', 
			region_name=self.region
		)

		if filters is not None:
			return self.client.describe_instances(
						Filters=filters
					)
		else:
			return self.client.describe_instances(
						InstanceIds=[self.myid]
					)

	def _own_tags(self):

		response = self._aws()
		return response['Reservations'][0]['Instances'][0]['Tags']

	
	def _own_info(self):

		info = {}
		my_tags = self._own_tags()
		for tag in my_tags:
			info[tag['Key']] = tag['Value']

		return info

	def members(self):

		for tag in self._own_tags():
			
			#Cluster Name
			if tag['Key'] == 'Cluster':
				cluster_name = str(tag['Value'])

			#Cluster Environment
			if tag['Key'] == 'Environment':
				env = str(tag['Value'])


		self.elastic = {}
		self.elastic['master_nodes'] = []
		self.elastic['data_nodes'] = []
		self.elastic['client_nodes'] = []

		#self.cluster_name = cluster_name
		#self.env = env
		
		filters =[
			{
				'Name': 'tag:Cluster',
				'Values': [cluster_name]
			},
			{
				'Name': 'tag:Environment',
				'Values': [env]
			},
			{
				'Name': 'instance-state-name',
				'Values': ['running']
			}
		]

		response = self._aws(filters)

		for reservation in response['Reservations']:
			for instance in reservation['Instances']:
				for tag in instance['Tags']:
					if tag['Key'] == "Name":
						node = {}
						node['name'] = tag['Value']
						node['private_ip'] = instance['PrivateIpAddress']
						if 'master' in tag['Value']:
							self.elastic['master_nodes'].append(node)
						elif 'data' in tag['Value']:
							self.elastic['data_nodes'].append(node)
						else:
							self.elastic['client_nodes'].append(node)
		return self.elastic
	
	def public_ip(self):

		all_hosts = []
		elastic = self.members()
		 
		for key, value in self.elastic.iteritems():
			for ip in self.elastic[key]:
				all_hosts.append(ip['public_ip'])
		return all_hosts

	def private_ip(self):

		all_hosts = []
		elastic = self.members()
		 
		for key, value in self.elastic.iteritems():
			for ip in self.elastic[key]:
				all_hosts.append(ip['private_ip'])
		return all_hosts

	def master_nodes(self):

		elastic = self.members()
		return sorted(self.elastic['master_nodes'], key=itemgetter('name'))
	
	def data_nodes(self):

		elastic = self.members()
		return sorted(self.elastic['data_nodes'], key=itemgetter('name'))

	def client_nodes(self):
		
		elastic = self.members()
		return sorted(self.elastic['client_nodes'], key=itemgetter('name'))



class Config(Info):

	params_struct = {
		'hostname': '',
		'cluster_name' : '',		#name of cluster
		'is_client': 'false', 		#is client node?
		'is_master': 'false', 		#is master node?
		'is_data': 'false', 		#is a data node?
		'http_enabled': 'false', 	#needs to response http requests?
		'cluster_members': []		#List of all nodes inthe cluster
	}

	def __init__(self):
		
		#To generate config it needs cluster info
		Info.__init__(self)
		

	def master_params(self):

		my_info = self._own_info()
		#Master parameter structure
		master_struc = Config.params_struct
		master_struc['hostname'] = my_info['Name']
		master_struc['cluster_name'] = my_info['Cluster']
		master_struc['is_master'] = 'true'
		master_struc['cluster_members'] = self.private_ip()

		return master_struc

	def data_params(self):

		my_info = self._own_info()
		#Master parameter structure
		data_struc = Config.params_struct
		data_struc['hostname'] = my_info['Name']
		data_struc['cluster_name'] = my_info['Cluster']
		data_struc['is_data'] = 'true'
		data_struc['cluster_members'] = self.private_ip()

		return data_struc

	def client_params(self):

		my_info = self._own_info()
		#Master parameter structure
		client_struc = Config.params_struct
		client_struc['hostname'] = my_info['Name']
		client_struc['cluster_name'] = my_info['Cluster']
		client_struc['is_client'] = 'true'
		client_struc['http_enabled'] = 'true'
		client_struc['cluster_members'] = self.private_ip()

		return client_struc

	def generate(self, tmlp_dir, tmpl_file, output_dir):
		"""
		This is where the old magic starts
		"""
		env = Environment(
			loader=FileSystemLoader(
				tmlp_dir
				)
			)

		template = env.get_template(tmpl_file)
		
		my_info = self._own_info()
		
		if my_info['Role'] == 'master':
			node_params = self.master_params()					
		
		elif my_info['Role'] == 'data':
			node_params = self.data_params()
		
		elif my_info['Role'] == 'client':
			node_params = self.client_params()
		
		else:
			raise Exception("Unrecognize node type")
			os.exit(1)

		node_params['cluster_members'].remove(self.myip)
		result = template.render(params=node_params)
		f = open(os.path.join(output_dir, 'elasticsearch.yml'), 'w')
		f.write(result)
		f.close()



if __name__ == "__main__":

	cluster = Config()
	template_dir = '/var/needish/ops/templates'
	template_file = 'elasticsearch.yml.j2'
	elasticsearch_config = '/usr/local/share/elasticsearch/config'
	cluster.generate(template_dir, template_file, elasticsearch_config)
