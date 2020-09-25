git clone --depth=1 https://github.com/jukedeck/nottingham-dataset.git corpus/abc/nottingham-dataset
curl http://marg.snu.ac.kr/chord_generation/dataset.zip > corpus/marg/dataset.zip
unzip corpus/marg/dataset.zip -d corpus/marg/
curl http://rockcorpus.midside.com/harmonic_analyses/rs200_harmony_clt.zip > corpus/rs/rs200_harmony_clt.zip
unzip corpus/rs/rs200_harmony_clt.zip -d corpus/rs
curl http://rockcorpus.midside.com/melodic_transcriptions/rs200_melody_nlt.zip > corpus/rs/rs200_melody_nlt.zip
unzip corpus/rs/rs200_melody_nlt.zip -d corpus/rs
