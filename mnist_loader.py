import os
import gzip
import shutil
from six.moves import urllib
from tensorflow.python.platform import gfile
import tensorflow as tf
import numpy as np
import math

class MnistData(object):

    def __init__(self, tf_dataset, one_hot, reshape):
        self.pos = 0
        self.images = None
        self.labels = None
        # load entire Dataset into memory by chunks of 10000
        tf_dataset = tf_dataset.batch(10000)
        tf_dataset = tf_dataset.repeat(1)
        features, labels = tf_dataset.make_one_shot_iterator().get_next()
        if not reshape:
            features = tf.reshape(features, [-1, 28, 28, 1])
        if one_hot:
            labels = tf.one_hot(labels, 10)
        with tf.Session() as sess:
            while True:
                try:
                    feats, labs = sess.run([features, labels])
                    self.images = feats if self.images is None else np.concatenate([self.images, feats])
                    self.labels = labs if self.labels is None else np.concatenate([self.labels, labs])
                except tf.errors.OutOfRangeError:
                    break


    def next_batch(self, batch_size):
        if self.pos+batch_size > len(self.images) or self.pos+batch_size > len(self.labels):
            self.pos = 0
        res = (self.images[self.pos:self.pos+batch_size], self.labels[self.pos:self.pos+batch_size])
        self.pos += batch_size
        return res


class Mnist(object):
    def __init__(self, train_dataset, test_dataset, one_hot, reshape):
        self.train = MnistData(train_dataset, one_hot, reshape)
        self.test = MnistData(test_dataset, one_hot, reshape)


def read_data_sets(data_dir, one_hot, reshape, validation_size=5000):
    train_images_file, train_labels_file, test_images_file, test_labels_file = load_mnist_data(data_dir)
    
    train_dataset = load_dataset(train_images_file, train_labels_file)
    train_dataset = train_dataset.shuffle(60000)
    
    test_dataset = load_dataset(test_images_file, test_labels_file)
    mnist = Mnist(train_dataset, test_dataset, one_hot, reshape)
    return mnist

def load_mnist_data(data_dir):
    SOURCE_URL = 'https://storage.googleapis.com/cvdf-datasets/mnist/'
    train_images_file = 'train-images-idx3-ubyte.gz'
    local_train_images_file = maybe_download_and_ungzip(train_images_file, data_dir, SOURCE_URL + train_images_file)
    train_labels_file = 'train-labels-idx1-ubyte.gz'
    local_train_labels_file = maybe_download_and_ungzip(train_labels_file, data_dir, SOURCE_URL + train_labels_file)
    test_images_file = 't10k-images-idx3-ubyte.gz'
    local_test_images_file = maybe_download_and_ungzip(test_images_file, data_dir, SOURCE_URL + test_images_file)
    test_labels_file = 't10k-labels-idx1-ubyte.gz'
    local_test_labels_file = maybe_download_and_ungzip(test_labels_file, data_dir, SOURCE_URL + test_labels_file)
    return local_train_images_file, local_train_labels_file, local_test_images_file, local_test_labels_file

def load_dataset(image_file, label_file):
    imagedataset = tf.data.FixedLengthRecordDataset(image_file, 28*28,
                                                    header_bytes=16, buffer_size=1024*16).map(read_image)
    labelsdataset = tf.data.FixedLengthRecordDataset(label_file, 1,
                                                     header_bytes=8, buffer_size=1024*16).map(read_label)
    dataset = tf.data.Dataset.zip((imagedataset, labelsdataset))
    return dataset

def maybe_download_and_ungzip(filename, work_directory, source_url):
    if filename[-3:] == ".gz":
        unzipped_filename = filename[:-3]
    else:
        unzipped_filename = filename

    if not gfile.Exists(work_directory):
        gfile.MakeDirs(work_directory)

    filepath = os.path.join(work_directory, filename)
    unzipped_filepath = os.path.join(work_directory, unzipped_filename)

    if not gfile.Exists(unzipped_filepath):
        urllib.request.urlretrieve(source_url, filepath)

        if not filename == unzipped_filename:
            with gzip.open(filepath, 'rb') as f_in:
                with open(unzipped_filepath, 'wb') as f_out: # remove .gz
                    shutil.copyfileobj(f_in, f_out)

        with gfile.GFile(filepath) as f:
            size = f.size()
        print('Successfully downloaded and unzipped', filename, size, 'bytes.')
    return unzipped_filepath

def read_label(tf_bytestring):
    label = tf.decode_raw(tf_bytestring, tf.uint8)
    return tf.reshape(label, [])

def read_image(tf_bytestring):
    image = tf.decode_raw(tf_bytestring, tf.uint8)
    return tf.cast(image, tf.float32)/256.0
