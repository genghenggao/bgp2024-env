from django.db import models

# Create your models here.
class GeoDiskIn(models.Model):
        filename= models.CharField
        firstkeywordcode= models.CharField(max_length=255) 
        firstkeywordrange= models.CharField(max_length=255)
        secondkeywordcode= models.CharField(max_length=255)
        secondkeywordrange= models.CharField(max_length=255)
        thirdkeywordcode= models.CharField(max_length=255) 
        thirdkeywordrange= models.CharField(max_length=255)
        foutrhkeywordcode= models.CharField(max_length=255) 
        fourthkeywordrange= models.CharField(max_length=255)
        fifthkeywordcode= models.CharField(max_length=255) 
        fifthkeywordrange= models.CharField(max_length=255)
        gatherflag= models.CharField(max_length=255) 
        tracetype= models.CharField(max_length=255) 
        userange= models.CharField(max_length=255) 
        timewindowinput= models.CharField(max_length=255) 
        headerword= models.CharField(max_length=255) 
        headerrange= models.CharField(max_length=255) 
        rangeword= models.CharField(max_length=255) 
        randomrange= models.CharField(max_length=255)
        gatherinput= models.CharField(max_length=255) 
        recreate= models.CharField(max_length=255) 
        headeronly= models.CharField(max_length=255) 
        sortsequence= models.CharField(max_length=255) 
        consistencycheck= models.CharField(max_length=255) 