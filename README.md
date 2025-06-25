New tool created: Microsynth auto-aligner
- Programatically takes microsynth sequencing data and generates an alignment, which is uploaded to Benchling
- The alignment is associated with the reference sequence on Benchling

Why I made it:
- Saves a lot of time spent manually aligning results on Snapgene / Geneious / Benchling
- Means everyone can generate and view alignments even without molbio softwares installed
- Centralises and stores all our sequencing data in our LIMS, so it can always be referenced back to
  
How to use it:
- Will be installed on Helix, or we can install it on anyones computer
- Follow the Benchling SOP for microsynth submission
- If the microsynth sample name is TUBEXXXX (your tube) and you have created your tubes properly, the aligner will do the rest!
- Download the data, then copy the path to the file and paste it into the program when prompted
- Alignments are then automatically uploaded to Benchling using the API and can be viewed from any computer
