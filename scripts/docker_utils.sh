set -e

get_all_reqd_images()
{
    FM_VERSION=$1
    all_reqd_images=$(docker-compose -f /app/static/docker_compose_v$FM_VERSION.yml config | grep image | awk '{print $2}')
    echo $all_reqd_images
}


is_image_available()
{
    image_name=$1
    if docker image inspect $image_name > /dev/null 2>&1 ; then
       echo "yes"
    else
       echo "no, $image_name not available"
    fi
}

are_all_dc_images_available()
{
   FM_VERSION=$1
   all_reqd_images=$(get_all_reqd_images $FM_VERSION)
   if [ -z "$all_reqd_images" ] ; then
     echo "Couldn't retrive required images from yml file"
     return
   fi
   for reqd_image in $all_reqd_images
   do
     available=$(is_image_available $reqd_image)
     if [ "$available" != "yes" ] ; then
        echo $available
        return
     fi
   done
   echo "yes"
}

