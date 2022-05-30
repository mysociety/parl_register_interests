---
name: regmem
title: Experimental Register of Members Interests
description: "Register of members interests with basic NLP extraction (unmaintained)\n"
version: 0.1
licenses:
- name: CC-BY-4.0
  path: https://creativecommons.org/licenses/by/4.0/
  title: Creative Commons Attribution 4.0 International License
contributors:
- title: mySociety
  path: https://mysociety.org
  role: author
resources:
- title: Processed Register of Members Interest
  description: Experimental process of May 2022 interests through basic NLP
  path: processed_regmem.csv
  name: processed_regmem
  profile: tabular-data-resource
  scheme: file
  format: csv
  hashing: md5
  encoding: utf-8
  schema:
    fields:
    - name: public_whip_id
      type: string
      description: Unique ID for a member based on public whip
      constraints:
        unique: false
      example: uk.org.publicwhip/person/10001
    - name: member_name
      type: string
      description: Name of the member
      constraints:
        unique: false
      example: Diane Abbott
    - name: registry_date
      type: string
      description: Date of the publication of this entry
      constraints:
        unique: false
      example: '2022-05-16'
    - name: category_type
      type: integer
      description: ID for the kind of disclosure
      constraints:
        unique: false
      example: 1
    - name: category_name
      type: string
      description: Descriptive name for the kind of disclosure
      constraints:
        unique: false
      example: Employment and earnings
    - name: free_text
      type: string
      description: The actual contents of the disclosure
      constraints:
        unique: false
      example: 'Payments from the Guardian, Kings Place, 90 York Way, London N1 9GU,
        for articles:'
    - name: extracted_orgs
      type: string
      description: Semi colon seperated list of ORG entities extracted from the free
        text
      constraints:
        unique: false
      example: Guardian; 9GU
    - name: extracted_money
      type: string
      description: Semi colon seperated list of MONEY entities extracted from the
        free text
      constraints:
        unique: false
      example: '100'
  download_id: regmem-processed-regmem
composite:
  xlsx: regmem-xlsx
---
