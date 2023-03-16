---
name: latest_register
title: Current release of Westminster Register of Members Interests
description: Register of members interests, with basic NLP processing. Current release
  only.
version: latest
licenses:
- name: CC-BY-4.0
  path: https://creativecommons.org/licenses/by/4.0/
  title: Creative Commons Attribution 4.0 International License
contributors:
- title: mySociety
  path: https://mysociety.org
  role: author
- title: UK Parliament
  path: https://www.parliament.uk/
  role: author
custom:
  formats:
    csv: true
    parquet: true
  build: parl_register_interests.__main__:download_and_build_latest
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
    0.1.0: ''
    0.1.1: 'Minor change in data for resource(s): register_of_interests'
    0.1.2: 'Minor change in data for resource(s): register_of_interests'
    0.1.3: 'Minor change in data for resource(s): register_of_interests'
    0.1.4: 'Minor change in data for resource(s): register_of_interests'
resources:
- title: Register of Members Interests (latest register)
  description: Register of members interests with basic NLP extraction
  custom:
    row_count: 5060
  path: register_of_interests.parquet
  name: register_of_interests
  profile: data-resource
  scheme: file
  format: parquet
  hashing: md5
  encoding: utf-8
  schema:
    fields:
    - name: public_whip_id
      type: string
      description: Public Whip ID for the member
      constraints:
        unique: false
      example: uk.org.publicwhip/person/10001
    - name: member_name
      type: string
      description: Name of member
      constraints:
        unique: false
      example: Aaron Bell
    - name: category_name
      type: string
      description: Category of interest
      constraints:
        unique: false
        enum:
        - Miscellaneous
        - Gifts, benefits and hospitality from UK sources
        - Visits outside the UK
        - Family members employed and paid from parliamentary expenses
        - Employment and earnings
        - 'Land and property portfolio: (i) value over £100,000 and/or (ii) giving
          rental income of over £10,000 a year'
        - (ii) Other shareholdings, valued at more than £70,000
        - '(i) Shareholdings: over 15% of issued share capital'
        - (a) Support linked to an MP but received by a local party organisation or
          indirectly via a central party organisation
        - No declared interests
        - (b) Any other support not included in Category 2(a)
        - Gifts and benefits from sources outside the UK
        - Family members engaged in lobbying the public sector on behalf of a third
          party or client
      example: (a) Support linked to an MP but received by a local party organisation
        or indirectly via a central party organisation
    - name: free_text
      type: string
      description: Free text description of interest
      constraints:
        unique: false
      example: '1 April 2022, payment of £100. Hours: 20 mins. (Registered 08 July
        2022)'
    - name: earliest_declaration
      type: string
      description: Earliest date this interest appeared in register
      constraints:
        unique: false
      example: '2009-11-25'
    - name: latest_declaration
      type: string
      description: Latest date this interest appeared in register
      constraints:
        unique: false
        enum:
        - '2023-03-06'
      example: '2023-03-06'
    - name: new_in_latest
      type: boolean
      description: Whether this interest is new in the latest register (true/false)
      constraints:
        unique: false
        enum:
        - false
        - true
      example: 'False'
    - name: extracted_orgs
      type: string
      description: Semi-colon separated list of organisations extracted from free
        text
      constraints:
        unique: false
      example: ''
    - name: extracted_sum
      type: string
      description: Semi-colon separated list of monetary values extracted from free
        text
      constraints:
        unique: false
      example: ''
  hash: 2c8fc8b49cac657404ece9242cd904b4
full_version: 0.1.4
permalink: /datasets/latest_register/latest
---
