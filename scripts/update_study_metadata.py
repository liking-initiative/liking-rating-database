#!/usr/bin/env python3
"""
Update existing study metadata with correct paper information and DOIs
"""
import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models.database import init_db, get_db, Study
from sqlalchemy import select, update

async def get_correct_metadata():
    """Get the correct study metadata"""
    return {
        'bakbot': {
            'name': 'Spacing of cue-approach training leads to better maintenance of behavioral change',
            'authors': ['Bakkour, A.', 'Botvinik-Nezer, R.', 'Cohen, N.', 'Hover, A. M.', 'Poldrack, R. A.', 'Schonberg, T.'],
            'year': 2018,
            'journal': 'PLOS ONE',
            'publication_title': 'Spacing of cue-approach training leads to better maintenance of behavioral change',
            'doi': '10.1371/journal.pone.0201580',
            'description': None
        },
        'bakpol': {
            'name': 'The hippocampus supports deliberation during value-based decisions',
            'authors': ['Bakkour, A.', 'Palombo, D. J.', 'Zylberberg, A.', 'Kang, Y. H.', 'Reid, A.', 'Verfaellie, M.', 'Shadlen, M. N.', 'Shohamy, D.'],
            'year': 2019,
            'journal': 'eLife',
            'publication_title': 'The hippocampus supports deliberation during value-based decisions',
            'doi': '10.7554/eLife.46080',
            'description': None
        },
        'balim': {
            'name': 'Investigating psychological mechanisms of self-controlled decisions for food and leisure activity',
            'authors': ['Bailey, C.', 'Lim, S.-L.'],
            'year': 2024,
            'journal': 'Journal of Behavioral Medicine',
            'publication_title': 'Investigating psychological mechanisms of self-controlled decisions for food and leisure activity',
            'doi': '10.1007/s10865-024-00469-3',
            'description': None
        },
        'brusaeb': {
            'name': 'Sources of confidence in value-based choice',
            'authors': ['Brus, J.', 'Aebersold, H.', 'Grueschow, M.', 'Polania, R.'],
            'year': 2021,
            'journal': 'Nature Communications',
            'publication_title': 'Sources of confidence in value-based choice',
            'doi': '10.1038/s41467-021-27618-5',
            'description': None
        },
        'deskrab': {
            'name': 'Decomposing preferences into predispositions and evaluations',
            'authors': ['Desai, N.', 'Krajbich, I.'],
            'year': 2021,
            'journal': 'Journal of Experimental Psychology: General',
            'publication_title': 'Decomposing preferences into predispositions and evaluations',
            'doi': '10.1037/xge0001162',
            'description': None
        },
        'eumdol': {
            'name': 'Peripheral Visual Information Halves Attentional Choice Biases',
            'authors': ['Eum, B.', 'Dolbier, S.', 'Rangel, A.'],
            'year': 2023,
            'journal': 'Psychological Science',
            'publication_title': 'Peripheral Visual Information Halves Attentional Choice Biases',
            'doi': '10.1177/09567976231184878',
            'description': None
        },
        'foljac': {
            'name': 'Explicit representation of confidence informs future value-based decisions',
            'authors': ['Folke, T.', 'Jacobsen, C.', 'Fleming, S. M.', 'De Martino, B.'],
            'year': 2016,
            'journal': 'Nature Human Behaviour',
            'publication_title': 'Explicit representation of confidence informs future value-based decisions',
            'doi': '10.1038/s41562-016-0002',
            'description': None
        },
        'ganzou': {
            'name': 'Computational Methods for Predicting and Understanding Food Judgment',
            'authors': ['Gandhi, N.', 'Zou, W.', 'Meyer, C.', 'Bhatia, S.', 'Walasek, L.'],
            'year': 2022,
            'journal': 'Psychological Science',
            'publication_title': 'Computational Methods for Predicting and Understanding Food Judgment',
            'doi': '10.1177/09567976211043426',
            'description': None
        },
        'gwikrab': {
            'name': 'Attitudes and attention',
            'authors': ['Gwinn, R.', 'Krajbich, I.'],
            'year': 2020,
            'journal': 'Journal of Experimental Social Psychology',
            'publication_title': 'Attitudes and attention',
            'doi': '10.1016/j.jesp.2019.103892',
            'description': None
        },
        'gwileb': {
            'name': 'The spillover effects of attentional learning on value-based choice',
            'authors': ['Gwinn, R. E.', 'Leber, A.', 'Krajbich, I.'],
            'year': 2019,
            'journal': 'Cognition',
            'publication_title': 'The spillover effects of attentional learning on value-based choice',
            'doi': '10.1016/j.cognition.2018.10.012',
            'description': None
        },
        'hasdes': {
            'name': 'Incentivized and non-incentivized liking ratings outperform willingness-to-pay in predicting choice',
            'authors': ['Hascher, J.', 'Desai, N.', 'Krajbich, I.'],
            'year': 2021,
            'journal': 'Judgment and Decision Making',
            'publication_title': 'Incentivized and non-incentivized liking ratings outperform willingness-to-pay in predicting choice',
            'doi': '10.1017/S1930297500008500',
            'description': None
        },
        'marglu': {
            'name': 'The Hungry Lens: Hunger Shifts Attention and Attribute Weighting in Dietary Choice',
            'authors': ['March, J.', 'Gluth, S.'],
            'year': 2025,
            'journal': 'eLife',
            'publication_title': 'The Hungry Lens: Hunger Shifts Attention and Attribute Weighting in Dietary Choice',
            'doi': '10.7554/eLife.103736.2',
            'description': None
        },
        'larlua': {
            'name': 'Increased BMI is associated with an altered decision-making process during healthy food choices in males and females',
            'authors': ['Larenas, G.', 'Luarte, L.', 'Kerr, B.', 'Ossandón, T.', 'Cortés, V.', 'Baudrand, R.', 'Pérez Leighton, C.'],
            'year': 2025,
            'journal': 'Appetite',
            'publication_title': 'Increased BMI is associated with an altered decision-making process during healthy food choices in males and females',
            'doi': '10.1016/j.appet.2025.107859',
            'description': None
        },
        'libain': {
            'name': 'Memorable but not chosen: No effect of memorability on value-based decisions',
            'authors': ['Li, X.', 'Bainbridge, W.', 'Bakkour, A.'],
            'year': 2022,
            'journal': 'Scientific Reports',
            'publication_title': 'Memorable but not chosen: No effect of memorability on value-based decisions',
            'doi': '10.1038/s41598-022-26333-5',
            'description': None
        },
        'romfred': {
            'name': 'Considering what we know and what we don\'t know: Expectations and confidence guide value integration in value-based decision-making',
            'authors': ['Frömer, R.', 'Callaway, F.', 'Griffiths, T. L.', 'Shenhav, A.'],
            'year': 2025,
            'journal': 'Open Mind',
            'publication_title': 'Considering what we know and what we don\'t know: Expectations and confidence guide value integration in value-based decision-making',
            'doi': '10.1162/opmi_a_00103',
            'description': None
        },
        'sepush': {
            'name': 'Visual attention modulates the integration of goal-relevant evidence and not value',
            'authors': ['Sepulveda, P.', 'Usher, M.', 'Davies, N.', 'Benson, A. A.', 'Ortoleva, P.', 'De Martino, B.'],
            'year': 2020,
            'journal': 'eLife',
            'publication_title': 'Visual attention modulates the integration of goal-relevant evidence and not value',
            'doi': '10.7554/eLife.60705',
            'description': None
        },
        'shenhav': {
            'name': 'Mutual inclusivity improves decision-making by smoothing out choice\'s competitive edge',
            'authors': ['Leng, X.', 'Frömer, R.', 'Summe, T.', 'Shenhav, A.'],
            'year': 2025,
            'journal': 'Nature Human Behaviour',
            'publication_title': 'Mutual inclusivity improves decision-making by smoothing out choice\'s competitive edge',
            'doi': '10.1038/s41562-024-02064-7',
            'description': None
        },
        'shevsmith': {
            'name': 'High-value decisions are fast and accurate, inconsistent with diminishing value sensitivity',
            'authors': ['Shevlin, B. R. K.', 'Smith, S. M.', 'Hausfeld, J.', 'Krajbich, I.'],
            'year': 2022,
            'journal': 'Proceedings of the National Academy of Sciences',
            'publication_title': 'High-value decisions are fast and accurate, inconsistent with diminishing value sensitivity',
            'doi': '10.1073/pnas.2101508119',
            'description': None
        },
        'smikrab': {
            'name': 'Mental representations distinguish value-based decisions from perceptual decisions',
            'authors': ['Smith, S. M.', 'Krajbich, I.'],
            'year': 2021,
            'journal': 'Psychonomic Bulletin & Review',
            'publication_title': 'Mental representations distinguish value-based decisions from perceptual decisions',
            'doi': '10.3758/s13423-021-01911-2',
            'description': None
        },
        'smikrab2018': {
            'name': 'Attention and choice across domains',
            'authors': ['Smith, S. M.', 'Krajbich, I.'],
            'year': 2018,
            'journal': 'Journal of Experimental Psychology: General',
            'publication_title': 'Attention and choice across domains',
            'doi': '10.1037/xge0000482',
            'description': None
        },
        'sucro': {
            'name': 'Elucidating the underlying components of food valuation in the human orbitofrontal cortex',
            'authors': ['Suzuki, S.', 'Cross, L.', 'O\'Doherty, J. P.'],
            'year': 2017,
            'journal': 'Nature Neuroscience',
            'publication_title': 'Elucidating the underlying components of food valuation in the human orbitofrontal cortex',
            'doi': '10.1038/s41593-017-0008-x',
            'description': None
        },
        'thomolt': {
            'name': 'Uncovering the computational mechanisms underlying many-alternative choice',
            'authors': ['Thomas, A. W.', 'Molter, F.', 'Krajbich, I.'],
            'year': 2021,
            'journal': 'eLife',
            'publication_title': 'Uncovering the computational mechanisms underlying many-alternative choice',
            'doi': '10.7554/elife.57012',
            'description': None
        },
        'toyam': {
            'name': 'Subjective Evaluation of Food: A Japanese Database',
            'authors': ['Toyama, A.', 'Yamashita, Y.', 'Suzuki, S.'],
            'year': 2025,
            'journal': 'OSF',
            'publication_title': 'Subjective Evaluation of Food: A Japanese Database',
            'doi': '10.31234/osf.io/ywt3k_v1',
            'description': None
        },
        'xuefoe': {
            'name': 'Neural Representations of Food-Related Attributes in the Human Orbitofrontal Cortex during Choice Deliberation in Anorexia Nervosa',
            'authors': ['Xue, A. M.', 'Foerde, K.', 'Walsh, B. T.', 'Steinglass, J. E.', 'Shohamy, D.', 'Bakkour, A.'],
            'year': 2022,
            'journal': 'Journal of Neuroscience',
            'publication_title': 'Neural Representations of Food-Related Attributes in the Human Orbitofrontal Cortex during Choice Deliberation in Anorexia Nervosa',
            'doi': '10.1523/JNEUROSCI.0958-21.2021',
            'description': None
        }
    }


async def update_study_metadata():
    """Update all existing studies with correct metadata"""
    print("🔧 Updating study metadata...")

    await init_db()

    metadata = await get_correct_metadata()
    updates_count = 0

    async for db in get_db():
        try:
            # Get all studies
            result = await db.execute(select(Study))
            studies = result.scalars().all()

            print(f"\nFound {len(studies)} studies in database")

            for study in studies:
                study_name_lower = study.name.lower()

                # Try to match by various patterns
                matched_key = None

                # Check for exact key matches in the name
                for key in metadata.keys():
                    if key in study_name_lower or study_name_lower.startswith(key):
                        matched_key = key
                        break

                # Also check by paper title similarity
                if not matched_key:
                    for key, meta in metadata.items():
                        if meta['name'].lower() in study_name_lower or study_name_lower in meta['name'].lower():
                            matched_key = key
                            break

                if matched_key:
                    meta = metadata[matched_key]
                    print(f"\n✓ Updating: {study.name}")
                    print(f"  → {meta['name']}")
                    print(f"  → DOI: {meta['doi']}")

                    # Update the study
                    study.name = meta['name']
                    study.authors = meta['authors']
                    study.year = meta['year']
                    study.journal = meta['journal']
                    study.publication_title = meta['publication_title']
                    study.doi = meta['doi']
                    study.description = meta['description']

                    updates_count += 1
                else:
                    print(f"\n⚠️  No metadata found for: {study.name}")

            # Commit all changes
            await db.commit()
            print(f"\n✅ Successfully updated {updates_count} studies")

        except Exception as e:
            print(f"❌ Error updating studies: {e}")
            await db.rollback()
            raise


async def main():
    """Main function"""
    print("=" * 60)
    print("Study Metadata Update Script")
    print("=" * 60)

    await update_study_metadata()

    print("\n" + "=" * 60)
    print("✅ Update complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
