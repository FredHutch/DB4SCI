#/bin/bash

# remove unused Docker images
docker images | \
while read -r image; do 
   if [[ $image = *'<none>'* ]]; then 
       read -r -a fields <<< "$image"
       echo remove: ${fields[2]} 
       docker rmi ${fields[2]}
   fi 
done

