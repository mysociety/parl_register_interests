---
name: regmem
title: Experimental Register of Members Interests
description: "Register of members interests with basic NLP extraction (unmaintained)\n"
version: latest
licenses:
- name: CC-BY-4.0
  path: https://creativecommons.org/licenses/by/4.0/
  title: Creative Commons Attribution 4.0 International License
contributors:
- title: mySociety
  path: https://mysociety.org
  role: author
custom:
  build: parl_register_experiment.__main__:download_and_build
  dataset_order: 1
  download_options:
    gate: default
    survey: default
    header_text: default
  composite:
    xlsx:
      include: all
      exclude: none
      render: true
    sqlite:
      include: all
      exclude: none
      render: true
    json:
      include: all
      exclude: none
      render: false
  change_log:
    0.1.0: Don't need to increment, first version
resources:
- title: Processed Register of Members Interest
  description: Experimental processessing of 2021-22 interests
  custom:
    row_count: 12351
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
      example: uk.org.publicwhip/person/26086
    - name: member_name
      type: string
      description: Name of the member
      constraints:
        unique: false
      example: Richard Foord
    - name: category_name
      type: string
      description: Descriptive name for the kind of disclosure
      constraints:
        unique: false
        enum:
        - Employment and earnings
        - (a) Support linked to an MP but received by a local party organisation or
          indirectly via a central party organisation
        - Miscellaneous
        - 'Land and property portfolio: (i) value over £100,000 and/or (ii) giving
          rental income of over £10,000 a year'
        - Gifts, benefits and hospitality from UK sources
        - (b) Any other support not included in Category 2(a)
        - '(i) Shareholdings: over 15% of issued share capital'
        - Family members engaged in lobbying the public sector on behalf of a third
          party or client
        - Visits outside the UK
        - (ii) Other shareholdings, valued at more than £70,000
        - Gifts and benefits from sources outside the UK
        - Family members employed and paid from parliamentary expenses
      example: Employment and earnings
    - name: earliest_declaration
      type: string
      description: Earliest register that this exact text declaration was made
      constraints:
        unique: false
      example: '2022-08-08'
    - name: latest_declaration
      type: string
      description: Latest register that this exact text declaration was made
      constraints:
        unique: false
      example: 2022-09-05 (latest)
    - name: free_text
      type: string
      description: The actual contents of the disclosure
      constraints:
        unique: false
      example: '28 July 2022, received final payment of £905.74. Hours: 3.95 hrs.
        (Registered 28 July 2022)'
    - name: extracted_orgs
      type: string
      description: Semi colon seperated list of ORG entities extracted from the free
        text (Experimental)
      constraints:
        unique: false
      example: Association of Liberal Democrat Councillors
    - name: extracted_sum
      type: string
      description: A sum of money extracted from the free text (Experimental)
      constraints:
        unique: false
      example: '905.74'
  hash: 944b41f91d248fefd8b408db65103b5b
  download_id: regmem-processed-regmem
full_version: 0.1.0
permalink: /datasets/regmem/latest
---
