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
      render: true
resources:
- title: Processed Register of Members Interest
  description: Experimental processessing of 2021-22 interests
  custom:
    row_count: 150752
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
      example: '2022-03-14'
    - name: category_type
      type: integer
      description: ID for the kind of disclosure
      constraints:
        unique: false
        enum:
        - 1
        - 4
        - 8
        - 3
        - 6
        - 9
        - 2
        - 7
        - 5
        - 10
      example: 1
    - name: category_name
      type: string
      description: Descriptive name for the kind of disclosure
      constraints:
        unique: false
        enum:
        - Employment and earnings
        - Visits outside the UK
        - Miscellaneous
        - Gifts, benefits and hospitality from UK sources
        - 'Land and property portfolio: (i) value over £100,000 and/or (ii) giving
          rental income of over £10,000 a year'
        - Family members employed and paid from parliamentary expenses
        - (b) Any other support not included in Category 2(a)
        - '(i) Shareholdings: over 15% of issued share capital'
        - (ii) Other shareholdings, valued at more than £70,000
        - Gifts and benefits from sources outside the UK
        - (a) Support linked to an MP but received by a local party organisation or
          indirectly via a central party organisation
        - Family members engaged in lobbying the public sector on behalf of a third
          party or client
      example: Employment and earnings
    - name: free_text
      type: string
      description: The actual contents of the disclosure
      constraints:
        unique: false
      example: 'Payments from the Guardian, Kings Place, 90 York Way, London N1 9GU,
        for articles:'
    - name: latest_entry
      type: boolean
      description: This entry is from the latest release of the register
      constraints:
        unique: false
        enum:
        - false
        - true
      example: 'False'
    - name: extracted_orgs
      type: string
      description: Semi colon seperated list of ORG entities extracted from the free
        text (Experimental)
      constraints:
        unique: false
      example: Viking Penguin; TV & Film Agency Ltd
    - name: extracted_sum
      type: string
      description: A sum of money extracted from the free text (Experimental)
      constraints:
        unique: false
      example: '300'
  hash: 387bffdf80a086afa591c25f7e07910a
  download_id: regmem-processed-regmem
full_version: 0.1
permalink: /datasets/regmem/latest
---
