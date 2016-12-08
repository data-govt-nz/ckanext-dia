from ckanext.spatial.model import MappedXmlDocument, ISOElement


class DIAISOResponsibleParty(ISOElement):

    elements = [
        ISOElement(
            name="contact-info",
            search_paths=[
                "gmd:contactInfo/gmd:CI_Contact",
            ],
            multiplicity="0..1",
            elements=[
                ISOElement(
                    name="phone",
                    search_paths=[
                        "gmd:phone/gmd:CI_Telephone/gmd:voice/gco:CharacterString/text()",
                    ],
                    multiplicity="0..1",
                ),
            ]
        )
    ]


class DIARights(ISOElement):

    elements = [
        ISOElement(
            name="use_limitation",
            search_paths=[
                "gmd:useLimitation/gco:CharacterString/text()"
            ],
            multiplicity="0..1"
        ),
        ISOElement(
            name="use_constraints",
            search_paths=[
                "gmd:useConstraints/gmd:MD_RestrictionCode/text()"
            ],
            multiplicity="0..1"
        ),
    ]


class DIADocument(MappedXmlDocument):

    elements = [
        ISOElement(
            name="language",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:language/gco:CharacterString/text()",
                # Original search strings from ckanext.spatial.models.harvested_metadata
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:language/gmd:LanguageCode/@codeListValue",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:language/gmd:LanguageCode/@codeListValue",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:language/gmd:LanguageCode/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:language/gmd:LanguageCode/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="jurisdiction",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicDescription/gmd:geographicIdentifier/gmd:MD_Identifier/gmd:code/gco:CharacterString/text()"
            ],
            multiplicity="0..1"
        ),
        DIAISOResponsibleParty(
            name="metadata-point-of-contact",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty",
            ],
            multiplicity="1..*",
        ),
        DIARights(
            name="rights",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints"
            ],
            multiplicity="*"
        )
    ]
