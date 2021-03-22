import cv2
import numpy as np
import argparse
import boto3
import xml.etree.ElementTree as ET # for parsing XML
from PIL import Image # to read images
from wand.image import Image as wi
from scipy import ndimage
import logging
from logging.handlers import RotatingFileHandler
from logging import handlers


parser = argparse.ArgumentParser(description='Image path.')
parser.add_argument('--image', help='Use path of images')
args = parser.parse_args()

template = cv2.imread('template_lobby.png',0)
w, h = template.shape[::-1]

def detect_lobby(file):

    img_color = cv2.imread(file)
    img = cv2.cvtColor(img_color, cv2.COLOR_BGR2GRAY)
    img2 = img.copy()
    meth = 'cv2.TM_SQDIFF_NORMED'
    #meth = 'cv2.TM_SQDIFF_NORMED'
    img = img2.copy()
    method = eval(meth)

    # Apply template Matching
    res = cv2.matchTemplate(img,template,method)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

    # If the method is TM_SQDIFF or TM_SQDIFF_NORMED, take minimum
    if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
        top_left = min_loc
    else:
        top_left = max_loc
    bottom_right = (top_left[0] + w, top_left[1] + h)

    if top_left[0]>img.shape[1]*0.1 or top_left[1]>img.shape[0]*0.1:
        return "None"

    cv2.rectangle(img_color,top_left, bottom_right, (0,255,0), 2)
    cv2.imshow("result", img_color)
    cv2.waitKey(0)
    #rect = [top_left[0], top_left[1], bottom_right[0], bottom_right[1]]
    return "Private Lobby"


def write_data_to_csv(pdf_file,df):
    logging.info('Writing data to csv. Check the data folder. Do not open the file until script is completed')
    directory = os.path.join(os.getcwd(),'data')
    if(os.path.isfile(os.path.join(directory, pdf_file.split('.')[0] + '_data.csv' ))):
        with open(os.path.join(directory, pdf_file.split('.')[0] + '_data.csv'), 'a') as f:
            df.to_csv(f, header= False, line_terminator='\n',index=False)
    else:
        with open(os.path.join(directory, pdf_file.split('.')[0] + '_data.csv'), 'a') as f:
            df.to_csv(f, header= False, line_terminator='\n',index=False)


def get_image(filename, bucket_name):
    image_processed=True
    client = boto3.client('s3', region_name='us-east-1')

    client.upload_file(filename, bucket_name, filename)

    s3BucketName = bucket_name
    objectName = filename
    
    logging.info('Image  {} loaded on bucket'.format(filename))
    client = boto3.client('textract')
    response = client.start_document_analysis(
     DocumentLocation={
    'S3Object': {
        'Bucket': s3BucketName,
        'Name': objectName
             }
      },
    FeatureTypes=['TABLES']
   )
    jobId = response['JobId']
    response = client.get_document_analysis(JobId=jobId)
    status = response["JobStatus"]
    logging.info("Job status of retreving data from api: {}".format(status))
    while(status == "IN_PROGRESS"):
        time.sleep(5)
        response = client.get_document_analysis(JobId=jobId)
        status = response["JobStatus"]
        logging.info("Job status: {}".format(status))
    pages = []

    time.sleep(5)
    
    if(status=="FAILED"):
        logging.info('Image could not be read. Moving it to unprocessed folder')
        image_processed = False

    response = client.get_document_analysis(JobId=jobId)

    pages.append(response)
    logging.info("Resultset page recieved: {}".format(len(pages)))
    nextToken = None

    if('NextToken' in response):
        nextToken = response['NextToken']

    while(nextToken):
        time.sleep(5)

        response = client.get_document_analysis(JobId=jobId, NextToken=nextToken)

        pages.append(response)
        logging.info("Resultset page recieved: {}".format(len(pages)))
        nextToken = None
        if('NextToken' in response):
            nextToken = response['NextToken']
            
            
    
    return pages,image_processed


def get_data_from_lobby(table_block, pages, image_file):
    logging.info('Retreiving Tables for the file')
    relationships = table_block['Relationships']
    table_cell_ids = relationships[0]['Ids']
    cell_blocks = []
    cell_relationship_blocks = {}
    data_missing_blocks = []
    
    missing_positions = []
    table_positions = []
    all_positions = []
    df = pd.DataFrame()
    for page in pages:
        for block in page['Blocks']:
            if(block['BlockType'] == 'CELL'):
                if(block['Id'] in table_cell_ids):
                #cell_blocks.append([block['Id'],block['RowIndex'], block['ColumnIndex']])
                    cell_blocks.append(block['Id'])
                    image_position,width,height = get_position_from_block(image_file,block)
                    table_positions.append([block['RowIndex'], block['ColumnIndex'],image_position,width,height])
                    all_positions.append([block['RowIndex'], block['ColumnIndex'],image_position,width,height])
                    df.loc[block['RowIndex'], block['ColumnIndex']] = ''
                    try:
                        cell_relationship_blocks[block['Id']] = [block['Relationships'][0]['Ids'],
                                                                 block['RowIndex'], block['ColumnIndex']]
                    except:
                        data_missing_blocks.append(block) 
                        cell_relationship_blocks[block['Id']] = [[''],block['RowIndex'], block['ColumnIndex']]
                        missing_positions.append([block['RowIndex'], block['ColumnIndex'],image_position,width,height])
                        continue
                           
                
    # Extra Text
    only_text_ids = []
    for page in pages:
        for block in page ['Blocks']:
               if(block['BlockType'] == 'LINE'):
                    only_text_ids.append(block)
    
    return df,data_missing_blocks,only_text_ids,missing_positions,table_positions,all_positions


def get_position_from_block(image_file, block):
    im = Image.open(image_file) 
    img = cv2.imread(image_file)
    
    height,width ,dummy = np.shape(img)#im.size
    new_image = np.zeros((height, width,3))
    w_geom = block['Geometry']['BoundingBox']['Width']
    h_geom = block['Geometry']['BoundingBox']['Height']
    l_geom = block['Geometry']['BoundingBox']['Left']
    t_geom = block['Geometry']['BoundingBox']['Top']
    h = int(h_geom*height)
    w = int(w_geom*width)
    x = int(l_geom*width)
    y = int(t_geom*height)              
    return (x,y),w,h


def create_cropped_image(data_missing_blocks,df,image_file):
    im = Image.open(image_file) 
    img = cv2.imread(image_file)
    
    height,width ,dummy = np.shape(img)#im.size
    new_image = np.zeros((height, width,3))
    print(np.shape(img))
    print(np.shape(new_image))
    
    
    i = 0
    image_positions = []
    for mb in data_missing_blocks:
        w_geom = mb['Geometry']['BoundingBox']['Width']
        h_geom = mb['Geometry']['BoundingBox']['Height']
        l_geom = mb['Geometry']['BoundingBox']['Left']
        t_geom = mb['Geometry']['BoundingBox']['Top']
        h = int(h_geom*height)
        w = int(w_geom*width)
        x = int(l_geom*width)
        y = int(t_geom*height)
        
        #if (w/h > 0.5):
            #continue
        crop_img = img[y:y+h, x:x+w]
        i = i + 1
        cv2.imwrite(os.path.join('cropped_images',"cropped" + str(i) + ".jpg"), crop_img)
        
        
        for my_i in range(h):
            for my_j in range(w):
                new_image[y+my_i,x+my_j,:] =  img[y+my_i,x+my_j,:]                 
        image_positions.append([mb['RowIndex'],mb['ColumnIndex'],(x,y)])
        logging.info('Loading the cropped image {}'.format('cropped_images',"cropped" + str(i) + ".jpg"))
        #pages_cropped = get_pages(os.path.join('cropped_images',"cropped" + str(i) + ".jpg"),bucket_name)
        #cv2.imwrite("cropped.jpg", crop_img)
        #cv2.imwrite("cropped.jpg", new_image)
        crop_text = ''
        #for page in pages_cropped:
            #for block in page['Blocks']:
                #if(block['BlockType'] == 'LINE'):
                    #crop_text = crop_text +  block['Text'] + ' '
        #if(df.loc[mb['RowIndex'],mb['ColumnIndex']] == ''):
            #df.loc[mb['RowIndex'],mb['ColumnIndex']] = crop_text
    cv2.imwrite("cropped_final.jpg", new_image)
    
    # fill missing data
    
    # Call get pages again and compare geometry to get the cell id and then get the text from it
    #
    return image_positions


def get_positions(image_file, blocks):
    im = Image.open(image_file) 
    img = cv2.imread(image_file)
    
    height,width ,dummy = np.shape(img)#im.size
    new_image = np.zeros((height, width,3))
    print(np.shape(img))
    print(np.shape(new_image))
    
    
    i = 0
    image_positions = []
    for mb in blocks:
        w_geom = mb['Geometry']['BoundingBox']['Width']
        h_geom = mb['Geometry']['BoundingBox']['Height']
        l_geom = mb['Geometry']['BoundingBox']['Left']
        t_geom = mb['Geometry']['BoundingBox']['Top']
        h = int(h_geom*height)
        w = int(w_geom*width)
        x = int(l_geom*width)
        y = int(t_geom*height)              
        image_positions.append([(x,y),mb['Text'],w,h])
    return image_positions


def fill_missing_data(data_missing_blocks,pages_cropped):
    cell_blocks = []
    cell_relationship_blocks = {}
    cell_geometry = {}
    for page in pages_cropped:
        for block in page['Blocks']:
            if(block['BlockType'] == 'CELL'):
                cell_geometry[str(block['Geometry'])] = block['Id']
                
                
    missing_position = []
    for db in data_missing_blocks:
        try:
            missing_position.append([cell_geometry[db['Geometry']],db['RowIndex'], db['ColumnIndex']])
        except:
            print(5)
                        
    return missing_position


# In[ ]:


def get_cropped_text_positions(image_file,pages_cropped,all_text_positions):
    cropped_text_positions = []
    for page in pages_cropped:
        if(page == True):
            continue
        try:
            for block in page['Blocks']:
                if(block['BlockType'] == 'LINE'):
                    image_position, width,height = get_position_from_block(image_file,block)
                    cropped_text_positions.append([image_position, block['Text'],width,height])
        except:
            for block in page[0]['Blocks']:
                if(block['BlockType'] == 'LINE'):
                    image_position, width,height = get_position_from_block(image_file,block)
                    cropped_text_positions.append([image_position, block['Text'],width,height])
    return cropped_text_positions


def get_missing_positions_reverse(missing_positions, all_text_positions):
    missing_poistions_updated = []
    distances = []
    for tp in all_text_positions:
        min_distance = 100000000000
        for mp in missing_positions:
            (mycell_centerx, mycell_centery) = ((mp[2][0] + mp[3]/2), (mp[2][1] + mp[4]/2))
            (mycell_centerx_t, mycell_centery_t) = ((tp[0][0] + tp[2]/2), (tp[0][1] + tp[3]/2))
            distance = calculateDistance((mycell_centerx, mycell_centery),(mycell_centerx_t, mycell_centery_t))
            #print('Coordinates are {} {} and min distance is {}',mp[2],tp[0],min_distance)
            #print(distance)
            #if(tp[1] == 'Berlin'):
               ## print(tp[0])
            #if((distance < min_distance) & ((mp[2][0] <= tp[0][0]) & (mp[2][1] <= tp[0][1]))):
                #min_distance = distance
                #distances = [distance,mp[0],mp[1],mp[2]]
            if((distance < min_distance)):
                min_distance = distance
                distances = [distance,mp[0],mp[1],mp[2],mp[3],mp[4]]
        if(len(distances) > 0):
            missing_poistions_updated.append([tp[0],tp[1],tp[2],tp[3],distances[0],distances[1],distances[2],distances[3],
                                              distances[4],distances[5]])
    return missing_poistions_updated


# In[ ]:


def get_cell_info(missing_positions_updated,row,column,df):
    data = []
    text = ''
    for mp in missing_positions_updated:
        if((mp[3] == row) & (mp[4] == column)):
            data.append([mp[0][0],mp[0][1],mp[1],mp[2],mp[3]])
    for d in sorted(data, key=lambda x: x[0]):
        if(str(d[2]) not in df.values):
            text = text + str(d[2]) + ' '
    return text


def detect_teams():
    folder_name = ''
    bucket_name = ''




if __name__ == '__main__':
    re = detect_lobby(args.image)
    print(re)





